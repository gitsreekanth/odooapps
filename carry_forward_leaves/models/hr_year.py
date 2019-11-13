# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class HRYear(models.Model):
    _name = 'hr.year'
    _description = 'HR Year'
    _order = "year"
    _rec_name = "year"

    @api.model
    def get_years(self):
        year_list = []
        for i in range(2009, 2050):
            year_list.append((str(i), str(i)))
        return year_list

    year = fields.Selection('get_years',string='Year')

    _sql_constraints = [
        ('year_uniq', 'unique (year)', 'Year must be unique !')
    ]