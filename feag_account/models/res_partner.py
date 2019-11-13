
from odoo import api, fields, models

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    # Get the Count of Customer Invoices
    # By default, smart button in partner shows amount in invoice. This will be changed to number.
    @api.multi
    def _sale_invoice_count(self):
        Invoice = self.env['account.invoice']
        for partner in self:
            partner.sale_invoice_count = Invoice.search_count([('partner_id', 'child_of', partner.id),
                                                                ('type', '=', 'out_invoice'),
                                                                ('state', 'not in', ['draft','cancel'])])

    sale_invoice_count = fields.Integer(compute='_sale_invoice_count', string='# Invoices')
