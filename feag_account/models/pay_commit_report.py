# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError, AccessError, ValidationError

# Financial Report - DB View
# ---------------------------
class payment_commit_report(models.Model):
    _name = "payment.commit.report"
    _auto = False

    date = fields.Date('Date')
    due_date = fields.Date('Due Date')
    amount = fields.Float('Amount')
    number = fields.Char('Details')
    partner_id = fields.Many2one('res.partner', 'Partner')
    type = fields.Char('Cashflow Type')
    subtype = fields.Char('Subtype')
    pay_priority = fields.Selection([
        ('assured', 'Assured Receipt'),
        ('planned', 'Planned Receipt'),
        ('unlikely', 'Unlikely Receipt'),
        ('mandatory', 'Mandatory Payment'),
        ('planned', 'Planned Payment'),
        ('deviating', 'Deviating Payment')
    ], string='Payment Priority')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'payment_commit_report')
        self._cr.execute("""
            CREATE VIEW payment_commit_report AS (
                
                select row_number() OVER () as id,type,subtype,number,partner_id,date,due_date,pay_priority,amount from
                (

                select
                id, 'Cash In' as type, 'AR' as subtype, number, partner_id, date_due as date, date_due as due_date, i.ci_pay_probability as pay_priority,
                (residual/(select rc.rate from res_currency_rate rc where
                rc.currency_id = i.currency_id order by id desc limit 1)) as amount
                from account_invoice i where type='out_invoice' and state = 'open'
                and id not in (select invoice_id from invoice_pay_commit_lines)

                union
               
                select
                pcl.id, 'Cash In' as type, 'AR' as subtype, i.number, i.partner_id, pcl.date, i.date_due as due_date, i.ci_pay_probability as pay_priority,
                (pcl.amount/(select rc.rate from res_currency_rate rc where
                rc.currency_id = i.currency_id order by id desc limit 1)) as amount
                from invoice_pay_commit_lines pcl
                left join account_invoice i on i.id = pcl.invoice_id
                where i.state = 'open' and i.type='out_invoice'

                union
               
                select
                id, 'Cash In' as type, 'Received' as subtype, name as number, partner_id, date, 
                date as due_date, 'NA' as pay_priority, credit as amount
                from account_move_line where credit > 0 and account_id = (select id from account_account where code = '122001')
                and date > cast(date_trunc('month', current_date) as date)

                union
               
                select
                id, 'Cash Out' as type, 'AP' as subtype, number, partner_id, date_due as date, date_due as due_date, i.vb_pay_priority as pay_priority,
                -(residual/(select rc.rate from res_currency_rate rc where
                rc.currency_id = i.currency_id order by id desc limit 1)) as amount
                from account_invoice i where type='in_invoice' and state = 'open'
                and id not in (select invoice_id from invoice_pay_commit_lines)
               
                union
               
                select
                pcl.id, 'Cash Out' as type, 'AP' as subtype, i.number, i.partner_id, pcl.date, i.date_due as due_date, i.vb_pay_priority as pay_priority,
                -(pcl.amount/(select rc.rate from res_currency_rate rc where
                rc.currency_id = i.currency_id order by id desc limit 1)) as amount
                from invoice_pay_commit_lines pcl
                left join account_invoice i on i.id = pcl.invoice_id
                where i.state = 'open' and i.type = 'in_invoice'

                union
               
                select
                id, 'Cash Out' as type, 'Paid' as subtype, name as number, partner_id, date, 
                date as due_date, 'NA' as pay_priority, -(debit) as amount
                from account_move_line where debit > 0 and account_id = (select id from account_account where code = '221001')
                and date > cast(date_trunc('month', current_date) as date)

                union

                select aoc.id, 'Cash Out' as type, (select name from account_other_cashflow_categ_main ac where ac.id = 
                (select other_cashflow_main_categ_id from account_other_cashflow_categ where id = aoc.other_cf_categ_id)) as subtype,
                (select name from account_other_cashflow_categ aocc where aocc.id = aoc.other_cf_categ_id) as number,
                aoc.partner_id, aoc.date, aoc.date as due_date, aoc.pay_priority, -(aoc.amount) as amount
                from account_other_cashflow aoc where state = 'open'

                union

                select aoc.id, 'Cash Out' as type, 'Paid' as subtype,
                (select name from account_other_cashflow_categ aocc where aocc.id = aoc.other_cf_categ_id) as number,
                aoc.partner_id, aoc.date, aoc.date as due_date, aoc.pay_priority, -(aoc.amount) as amount
                from account_other_cashflow aoc where state = 'paid' and aoc.date > cast(date_trunc('month', current_date) as date)

                ) as tbl

            )""")
