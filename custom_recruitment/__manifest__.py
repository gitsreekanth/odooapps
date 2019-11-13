##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2019 Sreekanth.
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
    'name': 'Recruitment Modifications',
    'version': '1.0',
    'category': 'HR',
    'summary': 'Recruitment Modifications',
    'author': 'Sreekanth',
    'website': 'http://www.elca.ae',
    'description': """Recruitment Modifications.""",
    'depends': ['hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/recruitment_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
