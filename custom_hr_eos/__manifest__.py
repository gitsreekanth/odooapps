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
    'name': 'End of Service Settlement',
    'version': '1.0',
    'category': 'HR',
	'summary': 'End of Service Settlement Customizations',
	'author': 'Sreekanth',
    'website': 'http://www.elca.ae',
    'description': """End of Service Settlement""",
    'depends': ['hr','hr_payroll',],
    'data': [
        'security/security_group.xml',
        'security/ir.model.access.csv', 
        'views/hr_gratuity_view.xml',
        'report/report_end_of_service.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
