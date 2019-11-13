# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class Holidays(models.Model):    
    _inherit = "hr.holidays"

    year = fields.Many2one('hr.year',string='Year',required=True,)
    carry_leave = fields.Boolean('Is Carry leave')
    leave_balance = fields.Float('Remaining Leave',compute='_compute_leave_balance')

    _sql_constraints = [
        ('date_check', "CHECK ( number_of_days_temp IS NOT NULL )", "The number of days must be not null."),
    ]

    @api.depends('date_from', 'date_to','holiday_status_id','employee_id')
    def _compute_leave_balance(self):
        """ Helper to compute the remaining leaves for the current employees
        :returns dict where the key is the employee id, and the value is the remain leaves
        """  
        if self.employee_id and self.holiday_status_id and self.year:
            sql_query = """
                SELECT
                    sum(h.number_of_days) AS days
                FROM
                    hr_holidays h
                    join hr_holidays_status s ON (s.id= %s)
                WHERE
                    h.state in ('deputy','validate','validate1','confirm') AND
                    s.id=h.holiday_status_id AND
                    h.employee_id = %s AND 
                    h.year = %s
                GROUP BY h.employee_id"""
            params = (self.holiday_status_id.id,self.employee_id.id,self.year.id,)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.fetchone()
            self.leave_balance = results[0] if results else 0.00
        else:
            self.leave_balance = 0.00
    
    @api.constrains('leave_balance','number_of_days_temp')
    def _check_leave_balance(self):
        """ Blocking if there is no sufficient leave for selected year """
        if self.type == 'remove' and not self.holiday_status_id.limit:
            if self.number_of_days_temp > self.leave_balance:
                raise ValidationError(_('The number of remaining leaves is not sufficient for this leave type.'))

    @api.onchange('date_from', 'date_to')
    def _default_year(self):
        """ Automating year form Duration, It will get the year from Durations when both years are same.
        Onchange validation for year is using if the year is not matching."""
        date_from = self.date_from
        date_to = self.date_to
        year = False
        if date_from and date_to:
            from_year  = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S').year
            from_to  = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S').year
            if from_year == from_to:
                now = from_year or from_to
                year = self.env['hr.year'].search([('year','=',now)],limit=1).id
            if from_year != from_to:
                raise ValidationError(_('The Start and End date has to be in the same year. Please apply for a separate leave for the next year'))
        if self.type == 'remove':
            self.year = year

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        """ Checking Duration Years in same year """
        if self.type == 'remove':
            for holiday in self:
                date_from  = datetime.strptime(holiday.date_from, '%Y-%m-%d %H:%M:%S').year or False
                date_to  = datetime.strptime(holiday.date_to, '%Y-%m-%d %H:%M:%S').year or False
                if date_from != date_to:
                    raise ValidationError(_('The Start and End date has to be in the same year. Please apply for a separate leave for the next year'))
        return super(Holidays,self)._check_date()

class HolidaysType(models.Model):
    _inherit = "hr.holidays.status"

    is_annual_leave = fields.Boolean('Is Annual Leave')
    max_carry_allowed = fields.Float('Max Carry Allowed')

    @api.constrains('is_annual_leave')
    def onchange_is_annual_leave(self):
        annual_leave_ids = []
        for status in self.env['hr.holidays.status'].search([]):
            for ids in status:
                if ids.is_annual_leave:
                    annual_leave_ids.append(ids.is_annual_leave)
        if len(annual_leave_ids) > len(set(annual_leave_ids)):
            raise ValidationError('Annual Leave is already Mapped for another Leave Type!')
