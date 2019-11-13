# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#
#    Copyright (c) All rights reserved:
#        (c) 2015  TM_FULLNAME
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses
#
###############################################################################
{
    'name': 'HR Carry Forward Leaves',
    'summary': 'Carry Forward Leaves for HR Module',
    'version': '1.0',
    'description': """HR Carry Forward Leaves""",
    'author': 'Sreekanth',
    'website': 'http://www.codersfort.com',
    'license': 'AGPL-3',
    'category': 'HR',
    'depends': [
        'base',
        'hr_holidays'
    ],
    'data':[
	    'security/ir.model.access.csv',        
    	'data/hr_year_data.xml',
        'data/hr_holidays_data.xml',
        'wizard/carry_forward_leaves_view.xml',
        'views/hr_year_view.xml',
        'views/hr_holidays_views.xml',
    ],
    'installable': True,
}
