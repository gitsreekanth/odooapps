# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError, RedirectWarning, ValidationError

# =============================================================================
#    Other Cash Out Flow
# =============================================================================
class AccountOtherCashflow(models.Model):
    _name = "account.other.cashflow"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    date = fields.Date('Date')
    amount  = fields.Float('Amount')
    other_cf_categ_id = fields.Many2one('account.other.cashflow.categ', 'Category')
    account_id = fields.Many2one('account.account', 'Account')
    partner_id = fields.Many2one('res.partner', 'Partner')
    pay_priority = fields.Selection([
        ('mandatory', 'Mandatory Payment'),
        ('planned', 'Planned Payment'),
        ('deviating', 'Deviating Payment')
    ], string='Payment Priority')
    state = fields.Selection([
        ('open', 'Open'),
        ('paid', 'Paid')
    ], string='Status', default='open', track_visibility='onchange')

# =============================================================================
#    Other Cash Out Flow Categories
# =============================================================================
class AccountOtherCashflowCateg(models.Model):
    _name = "account.other.cashflow.categ"

    other_cashflow_main_categ_id = fields.Many2one('account.other.cashflow.categ.main', 'Main Category')
    name = fields.Char('Name')

class AccountOtherCashflowCategMain(models.Model):
    _name = "account.other.cashflow.categ.main"

    name = fields.Char('Name')