##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Shawn.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'FEAG Generic Account Customization',
    'version': '1.1',
    'category': 'General',
	'summary': 'Apply Account customizations',
	'author': 'Sreekanth',
    'website': 'http://www.epillars.com',
    'description': """Apply generic client customizations to override default names and bindings.""",
    'depends': ['base','account','custom_crm','feag_header_footer'],
    'data': [
        'security/ir_group.xml',
        'security/ir.model.access.csv',
        'views/account_invoice_view.xml',
        'views/report_invoice.xml',
	'views/report_journal_entry.xml',
        'views/res_bank_demo.xml',
        'views/partner_view.xml',
        'views/other_cf_config.xml',
        'views/pay_commit_report_view.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
