# -*- coding: utf-8 -*-
from odoo import _, api, exceptions, fields, models

class AccMoveReport(models.Model):
    _inherit = 'account.move'

    def print_journal_entry(self):
        return self.env['report'].get_action(self, 'feag_account.tmpte_journal_entry')

# Restrict Journal Entries to be passed on Receivable/Payable without Partner reference
# ----------------------------------
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _get_reconcile(self, account):
        return account.reconcile

    @api.multi
    def _get_reconcile_msg(self):
        for move_line in self:
            reconcile = self._get_reconcile(move_line.account_id)
            if reconcile and not move_line.partner_id:
                return _("Reconciliation is set on account "
                         "%s '%s' so you must select partner on "
                         "the account move line with label '%s'."
                         ) % (move_line.account_id.code,
                              move_line.account_id.name,
                              move_line.name)

    @api.constrains('partner_id', 'account_id')
    def _check_partner_required(self):
        for rec in self:
            message = rec._get_reconcile_msg()
            if message:
                raise exceptions.ValidationError(message)