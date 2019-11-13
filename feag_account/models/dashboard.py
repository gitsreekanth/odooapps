# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
from ast import literal_eval
from babel.dates import format_datetime, format_date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError, ValidationError

class account_journal(models.Model):
    _inherit = "account.journal"

    # Accounting Dashboard
    # Inherited from account/models/account_journal_dashboard.py
    # By default, the values were showing based on Invoice date. This logic is changed to due date
    # Suppressed the value of 'Past' value.
    # ---------------------------------------------------------
    @api.multi
    def get_bar_graph_datas(self):
        data = []
        today = datetime.strptime(fields.Date.context_today(self), DF)
        data.append({'label': _('Past'), 'value': 0.0, 'type': 'past'})
        day_of_week = int(format_datetime(today, 'e', locale=self._context.get('lang') or 'en_US'))
        first_day_of_week = today + timedelta(days=-day_of_week + 1)
        for i in range(-1, 4):
            if i == 0:
                label = _('This Week')
            elif i == 3:
                label = _('Future')
            else:
                start_week = first_day_of_week + timedelta(days=i * 7)
                end_week = start_week + timedelta(days=6)
                if start_week.month == end_week.month:
                    label = str(start_week.day) + '-' + str(end_week.day) + ' ' + format_date(end_week, 'MMM',
                                                                                              locale=self._context.get(
                                                                                                  'lang') or 'en_US')
                else:
                    label = format_date(start_week, 'd MMM',
                                        locale=self._context.get('lang') or 'en_US') + '-' + format_date(end_week,
                                                                                                         'd MMM',
                                                                                                         locale=self._context.get(
                                                                                                             'lang') or 'en_US')
            data.append({'label': label, 'value': 0.0, 'type': 'past' if i < 0 else 'future'})

        # Build SQL query to find amount aggregated by week
        select_sql_clause = """SELECT sum(residual_company_signed) as total, min(date_due) as aggr_date from account_invoice where journal_id = %(journal_id)s and state = 'open'"""
        query = ''
        start_date = (first_day_of_week + timedelta(days=-7))
        for i in range(0, 6):
            if i == 0:
                query += "(" + select_sql_clause + " and date_due < '" + start_date.strftime(DF) + "')"
            elif i == 5:
                query += " UNION ALL (" + select_sql_clause + " and date_due >= '" + start_date.strftime(DF) + "')"
            else:
                next_date = start_date + timedelta(days=7)
                query += " UNION ALL (" + select_sql_clause + " and date_due >= '" + start_date.strftime(
                    DF) + "' and date_due < '" + next_date.strftime(DF) + "')"
                start_date = next_date

        self.env.cr.execute(query, {'journal_id': self.id})
        query_results = self.env.cr.dictfetchall()
        for index in range(0, len(query_results)):
            if query_results[index].get('aggr_date') != None and index > 0:
                data[index]['value'] = query_results[index].get('total')

        return [{'values': data}]

    # Accounting Dashboard
    # Inherited from account/models/account_journal_dashboard.py
    # In dashboard, awaiting payments was showing the total invoice amount rather than due amount. This is fixed.
    # ---------------------------------------------------------
    @api.multi
    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        number_to_reconcile = last_balance = account_sum = 0
        ac_bnk_stmt = []
        title = ''
        number_draft = number_waiting = number_late = 0
        sum_draft = sum_waiting = sum_late = 0.0
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)],
                                                                       order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            # Get the number of items to reconcile for that bank journal
            self.env.cr.execute("""SELECT COUNT(DISTINCT(statement_line_id)) 
                            FROM account_move where statement_line_id 
                            IN (SELECT line.id 
                                FROM account_bank_statement_line AS line 
                                LEFT JOIN account_bank_statement AS st 
                                ON line.statement_id = st.id 
                                WHERE st.journal_id IN %s and st.state = 'open')""", (tuple(self.ids),))
            already_reconciled = self.env.cr.fetchone()[0]
            self.env.cr.execute("""SELECT COUNT(line.id) 
                                FROM account_bank_statement_line AS line 
                                LEFT JOIN account_bank_statement AS st 
                                ON line.statement_id = st.id 
                                WHERE st.journal_id IN %s and st.state = 'open'""", (tuple(self.ids),))
            all_lines = self.env.cr.fetchone()[0]
            number_to_reconcile = all_lines - already_reconciled
            # optimization to read sum of balance from account_move_line
            account_ids = tuple(filter(None, [self.default_debit_account_id.id, self.default_credit_account_id.id]))
            if account_ids:
                amount_field = 'balance' if (
                            not self.currency_id or self.currency_id == self.company_id.currency_id) else 'amount_currency'
                query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s AND date <= %%s;""" % (
                amount_field,)
                self.env.cr.execute(query, (account_ids, fields.Date.today(),))
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get('sum') != None:
                    account_sum = query_results[0].get('sum')
        # TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
            # optimization to find total and sum of invoice that are in draft, open state
            query = """SELECT state, amount_total, residual, currency_id AS currency, type FROM account_invoice WHERE journal_id = %s AND state NOT IN ('paid', 'cancel');"""
            self.env.cr.execute(query, (self.id,))
            query_results = self.env.cr.dictfetchall()
            today = datetime.today()
            query = """SELECT amount_total, residual, currency_id AS currency, type FROM account_invoice WHERE journal_id = %s AND date < %s AND state = 'open';"""
            self.env.cr.execute(query, (self.id, today))
            late_query_results = self.env.cr.dictfetchall()
            for result in query_results:
                if result['type'] in ['in_refund', 'out_refund']:
                    factor = -1
                else:
                    factor = 1
                cur = self.env['res.currency'].browse(result.get('currency'))
                if result.get('state') in ['draft', 'proforma', 'proforma2']:
                    number_draft += 1
                    sum_draft += cur.compute(result.get('amount_total'), currency) * factor
                elif result.get('state') == 'open':
                    number_waiting += 1
                    sum_waiting += cur.compute(result.get('residual'), currency) * factor
            for result in late_query_results:
                if result['type'] in ['in_refund', 'out_refund']:
                    factor = -1
                else:
                    factor = 1
                cur = self.env['res.currency'].browse(result.get('currency'))
                number_late += 1
                sum_late += cur.compute(result.get('residual'), currency) * factor

        difference = currency.round(last_balance - account_sum) + 0.0
        return {
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, currency.round(account_sum) + 0.0, currency_obj=currency),
            'last_balance': formatLang(self.env, currency.round(last_balance) + 0.0, currency_obj=currency),
            'difference': formatLang(self.env, difference, currency_obj=currency) if difference else False,
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, currency.round(sum_draft) + 0.0, currency_obj=currency),
            'sum_waiting': formatLang(self.env, currency.round(sum_waiting) + 0.0, currency_obj=currency),
            'sum_late': formatLang(self.env, currency.round(sum_late) + 0.0, currency_obj=currency),
            'currency_id': currency.id,
            'bank_statements_source': self.bank_statements_source,
            'title': title,
        }

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Inherited from account/models/partner.py
    # While clicking on Invoiced smart button from partner, it was showing Invoices and VB
    # Fixed using the latest odoo default codebase
    # ---------------------------------------------------------
    def open_partner_history(self):
        action = self.env.ref('account.action_invoice_refund_out_tree').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.ids))
        return action
