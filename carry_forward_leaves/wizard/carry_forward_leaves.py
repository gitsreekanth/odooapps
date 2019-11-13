# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CarryForwardLeave(models.TransientModel):
    _name='carry.forward.leaves'
    _description = 'Carry Forward Leave'

    year = fields.Many2one('hr.year',string='Carry from Year',required=True)
    carry_forward_lines = fields.One2many('carry.forward.leaves.lines','forward_id','Lines')
    year_to = fields.Char(string='Carry forward to',compute='_compute_year_to')
    company_id = fields.Many2one('res.company',string='Company')
    max_carry_allowed = fields.Char('Max Carry Allowed')

    @api.depends('year')
    def _compute_year_to(self):
        for record in self:
            if record.year:
                record.year_to = str(int(record.year.year) + 1)
    
    @api.onchange('year','company_id')
    def get_employee_leaves(self):
        leave_id = self.env['ir.model.data'].get_object_reference('carry_forward_leaves', 'holiday_status_annual_leaves')[1]
        emp_obj = self.env['hr.employee']
        emp_sea = emp_obj.search([('company_id','=',self.company_id.id)])
        max_carry = self.env['hr.holidays.status'].search([('id','=',leave_id)])
        lines = []        
        if self.year:
            for emp in emp_sea:           
                leave_balance = self._get_remaining_leaves(emp.id,leave_id,self.year.id)
                carry = 0.0

                if leave_balance > max_carry.max_carry_allowed:                    
                    carry = max_carry.max_carry_allowed                
                
                if leave_balance <= max_carry.max_carry_allowed:                    
                    carry = leave_balance

                if leave_balance >0:
                    lines.append((0, 0, {
                                        'employee_id': emp.id,
                                        'leave_balance': leave_balance,
                                        'carry': carry,
                                        }))                
        self.update({
                    'carry_forward_lines': lines,
                    'max_carry_allowed': max_carry.max_carry_allowed                 
                    })
    
    
    def _get_remaining_leaves(self,employee_id,leave_id,year):
        """ Helper to compute the remaining leaves for the current employees
        :returns dict where the key is the employee id, and the value is the remain leaves
        """
        if employee_id and leave_id and year:
            sql_query = """
                SELECT
                    sum(h.number_of_days) AS days
                FROM
                    hr_holidays h
                    join hr_holidays_status s ON (s.id= %s)
                WHERE
                    h.state='validate' AND
                    s.limit=False AND
                    h.employee_id = %s AND 
                    h.year = %s AND
                    h.holiday_status_id= %s
                GROUP BY h.employee_id"""
            params = (leave_id,employee_id,year,leave_id)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.fetchone()
            return results[0] if results else 0.0
    
    @api.multi
    def button_carry_forward_leaves(self):        
        hr_holidays_obj = self.env['hr.holidays']
        leave_id = self.env['ir.model.data'].get_object_reference('carry_forward_leaves', 'holiday_status_annual_leaves')[1]
        max_carry = self.env['hr.holidays.status'].search([('id','=',leave_id)])
        year_to = self.env['hr.year'].search([('year','=',self.year_to)],limit=1)
        for line in self.carry_forward_lines:
            if line.carry > 0 :            
                allocation_id = hr_holidays_obj.create({
                                'holiday_status_id':leave_id,
                                'name':'Leave carried forward to %s'%(year_to.year),
                                'number_of_days_temp':line.carry,
                                'type':'add',
                                'year':year_to.id,
                                'employee_id':line.employee_id.id,
                                'carry_leave': True,
                                })
                
                negative_allocation_id = hr_holidays_obj.create({
                                'holiday_status_id':leave_id,
                                'name':'Leave carried forward from %s'%(self.year.year),
                                'number_of_days_temp':-(line.carry),
                                'type':'add',
                                'year':self.year.id,
                                'employee_id':line.employee_id.id,
                                'carry_leave': True,
                                })
                
                if allocation_id and negative_allocation_id:
                    allocation_id.action_confirm()
                    allocation_id.action_approve()
                    allocation_id.action_validate()

                    negative_allocation_id.action_confirm()
                    negative_allocation_id.action_approve()
                    negative_allocation_id.action_validate()
            
            if line.lapse > 0 :
                laps_allocation_id = hr_holidays_obj.create({
                                'holiday_status_id':leave_id,
                                'name':'Leave lapsed in year %s' %(self.year.year),
                                'number_of_days_temp':-(line.lapse),
                                'type':'add',
                                'year':self.year.id,
                                'employee_id':line.employee_id.id,
                                'carry_leave': True,
                                })

                if laps_allocation_id:
                    laps_allocation_id.action_confirm()
                    laps_allocation_id.action_approve()
                    laps_allocation_id.action_validate()
                
            if line.carry == 0.00:
                raise ValidationError(_('Leave allocation with Zero value is not allowed, Please check employee - %s')% (line.employee_id.name,))

class CarryForwardLeaveLines(models.TransientModel):
    _name ='carry.forward.leaves.lines'

    employee_id = fields.Many2one('hr.employee',string='Employee')
    leave_balance = fields.Float('Leave Balance')
    carry = fields.Float(String='Carry')
    lapse = fields.Float(String='Lapse',compute='_compute_lapse')
    forward_id =  fields.Many2one('carry.forward.leaves',string='Parent')

    @api.constrains('carry')
    def _check_carry(self):
        for record in self:            
            if self.carry > self.leave_balance:
                raise ValidationError(_('Carry days must be less than Leave Balace, Please check employee - %s')% (self.employee_id.name,))


    @api.depends('carry')
    def _compute_lapse(self):
        for record in self:
            if record.leave_balance > 0:                
                if record.carry <= record.leave_balance:                   
                    record.lapse = record.leave_balance - record.carry
            if record.carry < 0:
                record.carry = 0.00
                record.lapse = 0.00