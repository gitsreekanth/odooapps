# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError, RedirectWarning, ValidationError


###############################################################################
#    Adding Additional fields for Account Invoice Line                        #
###############################################################################

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    so_price_unit = fields.Float(string='SO Unit Price')
    so_net_total  = fields.Float(string='SO Net Total',compute='_compute_so_net_total')
    item_no = fields.Char('Item')
    tax_amount = fields.Float('Tax Amount', compute='_compute_line_tax')

    @api.multi
    def _compute_so_net_total(self):
        for record in self:
            record.so_net_total = record.so_price_unit * record.quantity

    # Calculate line tax amount
    # -------------------------
    @api.multi
    def _compute_line_tax(self):
        for record in self:
            if record.invoice_line_tax_ids:
                for taxes in record.invoice_line_tax_ids:
                    record.tax_amount += round((record.quantity * record.price_unit) * taxes.amount / 100, 2)

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    iban_no = fields.Char('IBAN No')
    branch_name = fields.Char('Branch Name')
    is_invoice = fields.Boolean(string='Default Invoice Bank')

    #validating only one bankaccount is asigned for invoicing
    @api.constrains('is_invoice')
    def _check_is_invoice_bank_account_set(self):
        invoice_ids = []
        for record in self.env['res.partner.bank'].search([]):
            if record.is_invoice:
                invoice_ids.append(record.is_invoice)
            if len(invoice_ids)> 1 and self.is_invoice:
                raise ValidationError("Default invoice bank details already assigned")

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    #calculating SO NET Total
    @api.depends('invoice_line_ids.so_net_total')
    def _amount_so_net_total(self):
        self.total_so_net_total = sum(line.so_net_total for line in self.invoice_line_ids)

    #getting default bank id from bank accounts
    @api.model
    def _default_invoice_bank_id(self):
        return self.env['res.partner.bank'].search([('is_invoice', '=', True)], limit=1)

    invoice_bank_id = fields.Many2one('res.partner.bank',string="Invoice Bank Details",default=_default_invoice_bank_id)
    total_so_net_total = fields.Monetary(string='SO Net Total',compute='_amount_so_net_total')
    po_number = fields.Char(string="PO Number")
    vendor_number = fields.Char(string="Vendor Number")
    project_ref_id = fields.Many2one('project.project',string="Project Ref.")
    dn_number = fields.Char(string="DN Number")
    dn_date = fields.Date(string="DN Date")
    project_payent_perc = fields.Float(string='Project Payment')
    account_analytic_id = fields.Many2one('account.analytic.account', related='invoice_line_ids.account_analytic_id', string='Analytic Account')
    second_address_id = fields.Many2one('res.partner', string="Delivery Address")
    pay_commit_lines = fields.One2many('invoice.pay.commit.lines', 'invoice_id', string='Payment Commitment')
    commit_due_match = fields.Boolean('Commit-Due Amt Match', compute='_commit_due_match', store=True)
    ci_pay_probability = fields.Selection([
        ('assured', 'Assured'),
        ('planned', 'Planned'),
        ('unlikely', 'Unlikely')
    ], string='Payment Probability', default='assured', copy=False)
    vb_pay_priority = fields.Selection([
        ('mandatory', 'Mandatory'),
        ('planned', 'Planned'),
        ('deviating', 'Deviating')
    ], string='Payment Priority', default='mandatory', copy=False)
    reference = fields.Char(string='Vendor Reference', copy=False,
                            help="The partner reference of this invoice.", readonly=False)
                            #states={'draft': [('readonly', False)]})
    state = fields.Selection([
            ('draft','Draft'),
            ('confirmed','Waiting Approval'),
            ('validate','Approved'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    #Confirm Invoice
    #---------------
    @api.multi
    def action_invoice_confirm(self):
        # Mandatory attachments for vendor bills
        if self.type == 'in_invoice':
            ir_attahment_obj = self.env['ir.attachment']
            ir_attachment_search = ir_attahment_obj.search([('res_model', '=', 'account.invoice'), ('res_id', '=', self.id)])
            if not ir_attachment_search:
                raise UserError('Please attach relevant documents before confirming')
        return self.write({'state': 'confirmed'})
    
    #Approve Invoice
    #---------------
    @api.multi
    def action_invoice_validate(self):
        return self.write({'state': 'validate'})
    
    #Override Cancel from account_cancel module
    #------------------------------------------
    @api.multi
    def action_invoice_cancel(self):
        if self.filtered(lambda inv: inv.state not in ['confirmed','proforma2', 'draft', 'open', 'validate']):
            raise UserError(_("Invoice must be in draft, approved or open state in order to be cancelled."))
        return self.action_cancel()

	#CHECK CODE: inherited from default code of account invoice (include approved state while checking invoice validation)
	#--------------------------------------------------------------
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft', 'validate']):
            raise UserError(_("Invoice must be in draft, approved or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate()
	
	#Avoid Duplication of Vendor Bills wrt reference
	#-----------------------------------------------
    @api.constrains('reference', 'partner_id')
    def _check_bill_duplicate(self):
        for bill in self:
			if bill.reference:
				domain = [
					('reference', '=', bill.reference),
					('partner_id', '=', bill.partner_id.id),
					]
				dupebills = self.sudo().search_count(domain)
				if dupebills > 1:
					raise ValidationError(_('Bill Already Entered'))
	
	#Messaging
	#---------
	@api.multi
	def _track_subtype(self, init_values):
		self.ensure_one()
		if 'state' in init_values and self.state == 'paid' and self.type in ('out_invoice', 'out_refund', 'in_invoice'):
			return 'account.mt_invoice_paid'
		elif 'state' in init_values and self.state == 'open' and self.type in ('out_invoice', 'out_refund', 'in_invoice'):
			return 'account.mt_invoice_validated'
		elif 'state' in init_values and self.state == 'draft' and self.type in ('out_invoice', 'out_refund', 'in_invoice'):
			return 'account.mt_invoice_created'
		elif 'state' in init_values and self.state == 'confirmed' and self.type in ('out_invoice', 'out_refund', 'in_invoice'):
			return 'account.mt_invoice_confirmed'
		return super(AccountInvoice, self)._track_subtype(init_values)

    # Check if Commitment and Residual amounts are matching
    # -----------------------------------------------------
    @api.depends('residual', 'pay_commit_lines')
    def _commit_due_match(self):
        for bill in self:
            match = True
            amount = 0
            if bill.pay_commit_lines:
                for lines in bill.pay_commit_lines:
                    amount += lines.amount
                if amount != bill.residual:
                    match = False
            bill.commit_due_match = match

    # Cash Payment (Quick Payment option)
    # ---------------------------------------------
    @api.multi
    def action_quick_pay(self):
        for order in self:

            # Block if partial payment has already been made
            if self.amount_total != self.residual:
                raise ValidationError(_('Cannot use quick payment option for partially paid bills!'))

            if order.move_id:
                # Cancel the entry
                order.move_id.button_cancel()

                # Find Journal and Account
                journal_id = self.env['account.journal'].search([('type', '=', 'cash')])
                account_id = journal_id.default_debit_account_id

                # Update Journal and Account
                order.move_id.write({'journal_id': journal_id.id})
                for movelines in order.move_id.line_ids:
                    if movelines.account_id.user_type_id.type == 'payable':
                        movelines.write({'account_id': account_id.id})

                # Post the entry
                order.move_id.post()
        return True

class Bank(models.Model):
    _inherit = 'res.bank'

    swift_code = fields.Char(string="Swift Code")
    routing_code = fields.Char('Routing Code')

# =================================================
# Payment Commitment section
# =================================================
class PaymentCommitLines(models.Model):
    _name = 'invoice.pay.commit.lines'

    invoice_id = fields.Many2one('account.invoice', string='Invoice', ondelete='cascade')
    date = fields.Date('Commitment Date')
    amount = fields.Float('Payment Amount')
