# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: eP System
#    Copyright 2017 ePillars Systems LLC
#
##############################################################################

import re
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import UserError, ValidationError

#=====================================================
# Gratuity Rules
#=====================================================
class hr_gratuity_rule(models.Model):    
    _name = 'hr.gratuity.rule'
    _description = "HR Gratuity Rule"

    name = fields.Char(string="Name")
    year = fields.Selection([('1', '1-5'), ('5', '5 & Above')], string='Year Slab')
    days = fields.Integer(string='Effective Days')
    
    _sql_constraints = [
        ('year_uniq', 'unique (year)', "Year must be unique!"),
    ]

#=====================================================
# Adding Date of Join field
#=====================================================
class hr_employee(models.Model):
    _inherit = 'hr.employee'

    date_of_join= fields.Date('Date of Joining')

#=====================================================
# Gratuity Settlement
#=====================================================
class hr_gratuity(models.Model):  
    _name = 'hr.gratuity'
    _rec_name = 'employee_id'
    _description = 'Gratuity Settlement'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    employee_id = fields.Many2one('hr.employee', string='Employee')
    first_working_date = fields.Date('First Working Date')
    last_working_date= fields.Date('Last Working Date')
    type= fields.Selection([('Resignation', 'Resignation'),('Termination','Termination')],string='Status')
    prepared_id = fields.Many2one('res.users', 'Prepared by', default=lambda self: self.env.user)
    approved_id = fields.Many2one('res.users', 'Approved by')
    total_days= fields.Integer('Total Days')
    amount= fields.Integer('Amount')
    gratuity_amount=fields.Float(compute='_get_gratuity_amount', string='Gratuity Amount', multi='sums')
    gratuity_days = fields.Float(compute='_get_gratuity_amount', string='Gratuity Days', multi='sums')
    total_eos_amount = fields.Float(compute='_get_values', string='Total EoS Amount', multi='sums')
    gratuity_line_ids= fields.One2many('hr.gratuity.line', 'gratuity_id', string='Gratuity Lines')
    gratuity_extra_lines= fields.One2many('hr.gratuity.extra', 'gratuity_id', string='Gratuity Additional Lines')
    salary_detail_lines = fields.One2many('hr.gratuity.salary.details', 'gratuity_id', string='Salary Detail Lines')
    leave_detail_lines = fields.One2many('hr.gratuity.leave.details', 'gratuity_id', string='Leave Detail Lines')
    company_id= fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('hr.employee'))
    contract = fields.Selection([
        ('Unlimited', 'Unlimited'),
        ('Limited', 'Limited'),
    ], string='Contract', default='Unlimited')
    state= fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
        ], string='Status', track_visibility='onchange',default='draft')
    
    _sql_constraints = [
        ('employee_id_uniq', 'unique(employee_id)', "You cannot have multiple gratuity settlement records for the same Employee"),
    ]

    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    onchange_employee_id
    # Description    :    Populate the details while selecting the employee
    #===============================================================================
    # @api.onchange('employee_id')
    # def onchange_employee_id(self):
    #     if self.employee_id:
    #         self.company_id = self.env['hr.employee'].browse(self.employee_id.id).company_id.id
    #         #self.company_id = self.env['hr.employee'].search([('id','=',self.employee_id.id)]).company_id.id
    #         remaining_leaves = self.env['hr.holidays'].browse(self.employee_id.id).company_id.id

    # Total Gratuity Amount
    # ---------------------
    @api.multi
    @api.onchange('gratuity_line_ids')
    def _get_gratuity_amount(self):
        res = {}
        for record in self:
            res[record.id] = {
                'gratuity_amount': 0.0,
                'gratuity_days': 0.0,
            }
            gratuity_amount = 0.0
            gratuity_days = 0.0

            if record.gratuity_line_ids:
                for lines in record.gratuity_line_ids:
                    gratuity_amount += lines.amount
                    gratuity_days += lines.total_days

            record.gratuity_amount = round(gratuity_amount,2)
            record.gratuity_days = round(gratuity_days,0)

    # Total EoS Amount
    # ----------------
    @api.multi
    @api.onchange('gratuity_line_ids','gratuity_extra_lines')
    def _get_values(self):
        res = {}
        for record in self:
            res[record.id] = {
                'total_eos_amount': 0.0,
            }
            amount1 = 0.0
            amount2 = 0.0
            total_eos_amount = 0.0
            
            if record.gratuity_line_ids:
                for lines1 in record.gratuity_line_ids:
                    amount1 += lines1.amount
            
            if record.gratuity_extra_lines:
                for lines2 in record.gratuity_extra_lines:
                    amount2 += lines2.amount
            
            total_eos_amount = amount1 + amount2
            record.total_eos_amount = round(total_eos_amount,2)


    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    calculate_gratuity
    # Description    :    Calculate the Gratuity Amount
    #===============================================================================
    # Calculations:
    #===============================================================================
    # 1) If the employee has Resigned, and if the service is:
    #
    #   (1A) 1 year to less than 3 years:
    #       Gratuity Amount = ((Annual Basic Salary /365) * 21 * Years Worked) / 3
    #
    #   (1B) 3 years to less than 5 years:
    #       Gratuity Amount = (Annual Basic Salary /365) * 21 * Years Worked * 2 / 3
    #
    #   (1C) for each additional year over 5 years: 30 days of basic salary
    #       Gratuity Amount = (Annual Basic Salary /365) * 30 * Years Worked
    #
    # 2) If the employee was Terminated and if the service is:
    #
    #   (2A) 1 to 5 years:
    #       Gratuity Amount = (Annual Basic Salary /365) * 21 * Years Worked
    #
    #   (2B) more than 5 years:
    #       Gratuity Amount = (Annual Basic Salary /365) * 30 * Years Worked
    #       (this will be for remaining years after 5; the first 5 will be based on 21)
    #
    # Where,
    # Annual Basic Salary = Last Paid Basic Salary * 12 and Years Worked = (Date of Leaving – Date of Joining) / 365
    #===============================================================================
    
    @api.multi
    def calculate_gratuity(self):
        total_days = total_amount = per_day_basic= 0        
        #Joining and Ending Dates
        if self.employee_id.date_of_join:
            join_date = datetime.strptime(self.employee_id.date_of_join,'%Y-%m-%d')            
        else:
            raise UserError(_('Please first set joining date for the employee !'))
        date_end = datetime.strptime(self.last_working_date, '%Y-%m-%d')
        self.first_working_date = join_date

        #Remove the existing gratuity lines while re-calculating
        gratuity_lines = []
        self.gratuity_line_ids.unlink()
        contract_ids = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id)])
        if contract_ids:
            contract_objs = self.env['hr.contract'].browse(contract_ids.id)
            if contract_objs[0].date_start:                
                contract_obj = contract_objs[-1]

                # Find Annual Salary and Per Day Basic Salary
                annual_salary = round(contract_obj.wage * 12)
                per_day_basic = annual_salary / 365.00

                # Store Salary details into sub table
                exist_sal_detail_ids = self.env['hr.gratuity.salary.details'].search([('gratuity_id', '=', self.id)])
                for ids in exist_sal_detail_ids:
                    exist_sal_detail_ids.unlink()

                sal_line_obj = self.env['hr.gratuity.salary.details']
                sal_line_obj.create({'gratuity_id': self.id,
                                     'name': 'Basic',
                                     'monthly': contract_obj.wage,
                                     'daily': contract_obj.wage *12 / 365})

                others_sal = 0
                for contract_lines in contract_objs.struct_id.rule_ids:
                    if contract_lines.amount_select == 'fix':
                        sal_line_obj.create({'gratuity_id': self.id,
                                             'name': contract_lines.name,
                                             'monthly': contract_lines.amount_fix,
                                             'daily': contract_lines.amount_fix * 12 / 365})
                        others_sal += contract_lines.amount_fix
                per_day_gross = round(contract_obj.wage + others_sal) * 12 / 365

                if date_end > join_date:

                    # If employee leaves After 5 years of service:
                    #------------------------------------------------                    
                    if join_date + relativedelta(years=5) < date_end:

                        # Calculation for 1-5 Years:                        
                        rule_ids1 =  self.env['hr.gratuity.rule'].search([('year', '=', '1')])
                        if rule_ids1:
                            date_end1 = (join_date + relativedelta(years=5)) - timedelta(days=1)
                            total_days = (date_end1 - join_date).days
                            effective_days = self.env['hr.gratuity.rule'].browse(rule_ids1.id).days
                            amount = (per_day_basic * effective_days * 5)
                            self.env['hr.gratuity.line'].create({
                                    'gratuity_id': self.id,
                                    'contract_id': contract_obj.id,
                                    'date_from': join_date,
                                    'date_to': date_end1,
                                    'total_days': total_days,
                                    'amount': amount
                            })
                        
                        # Calculation for > 5 Years:
                        rule_ids2 = self.env['hr.gratuity.rule'].search([('year', '=', '5')])
                        if rule_ids2:
                            date_start2 = (join_date + relativedelta(years=5))
                            total_days = (date_end - date_start2).days
                            total_years = total_days / 365.00
                            effective_days = self.env['hr.gratuity.rule'].browse(rule_ids2.id).days
                            amount = (per_day_basic * effective_days * total_years)
                            self.env['hr.gratuity.line'].create({
                                    'gratuity_id': self.id,
                                    'contract_id': contract_obj.id,
                                    'date_from': date_start2,
                                    'date_to': date_end,
                                    'total_days': total_days,
                                    'amount': amount
                                    })
                            
                    
                    # If employee leaves within 5 years
                    #-------------------------------------
                    else:
                        
                        # Resignation:
                        # -----------
                        if self.type == 'Resignation':
                            
                            # If employee leaves after 3 years
                            #------------------------------------
                            if join_date + relativedelta(years=3) < date_end:                                
                                # Calculation for 1-5 Years
                                rule_ids2 = self.env['hr.gratuity.rule'].search([('year', '=', '1')])                                
                                if rule_ids2:
                                    total_days = (date_end-join_date).days
                                    total_years = total_days / 365.00
                                    effective_days = self.env['hr.gratuity.rule'].browse(rule_ids2.id).days
                                    amount = (per_day_basic * effective_days * total_years) * 2 / 3
                                    self.env['hr.gratuity.line'].create({
                                        'gratuity_id': self.id,
                                        'contract_id': contract_obj.id,
                                        'date_from': join_date,
                                        'date_to': date_end,
                                        'total_days': total_days,
                                        'amount': amount
                                        })
                                                                  
                                    
                            # If employee leaves within 3 years:
                            #------------------------------------
                            else:
                                # Calculation for 1-3 Years
                                rule_ids1 = self.env['hr.gratuity.rule'].search([('year', '=', '1')])                                
                                if rule_ids1:
                                    total_days = (date_end-join_date).days
                                    total_years = total_days / 365.00
                                    effective_days = self.env['hr.gratuity.rule'].browse(rule_ids1.id).days
                                    amount = (per_day_basic * effective_days * total_years) / 3
                                    self.env['hr.gratuity.line'].create({
                                        'gratuity_id': self.id,
                                        'contract_id': contract_obj.id,
                                        'date_from': join_date,
                                        'date_to': date_end,
                                        'total_days': total_days,
                                        'amount': amount
                                       })
                                                                       
                        
                        # Termination:
                        # -----------
                        elif self.type == 'Termination':
                        
                            # Calculation for 1-5 Years
                            rule_ids1 = self.env['hr.gratuity.rule'].search([('year', '=', '1')])
                            if rule_ids1:
                                total_days = (date_end-join_date).days
                                total_years = total_days / 365.00
                                effective_days =  self.env['hr.gratuity.rule'].browse(rule_ids1.id).days
                                amount = (per_day_basic * effective_days * total_years)
                                self.env['hr.gratuity.line'].create({
                                    'gratuity_id': self.id,
                                    'contract_id': contract_obj.id,
                                    'date_from': join_date,
                                    'date_to': date_end,
                                    'total_days': total_days,
                                    'amount': amount
                                    })
                                
        # Get Leave Records
        # -----------------
        leaves_eligible=0
        leaves_taken=0
        leaves_remaining=0
        start_date_year = datetime.now().strftime('%Y-01-01 00:00:00')
        end_date_year= datetime.now().strftime('%Y-12-31 23:59:59')

        # Total Leaves Allocation
        self.env.cr.execute("""select sum(number_of_days) from hr_holidays where employee_id=%s and type='add' 
                                and state='validate' and holiday_status_id=(select id from hr_holidays_status 
                                where is_annual_leave=True) """, [self.employee_id.id])
        leaves_eligible = self.env.cr.fetchone()[0] or 0
        # Total Leaves Taken
        self.env.cr.execute("""select abs(sum(number_of_days)) from hr_holidays where employee_id=%s and type='remove' 
                                and state='validate' and holiday_status_id=(select id from hr_holidays_status 
                                where is_annual_leave=True) """, [self.employee_id.id])
        leaves_taken = self.env.cr.fetchone()[0] or 0
        # Total Remaining Leaves
        leaves_remaining = leaves_eligible - leaves_taken

        # Clear leave details from sub table
        leave_line_obj = self.env['hr.gratuity.leave.details']
        exist_leave_detail_ids = leave_line_obj.search([('gratuity_id', '=', self.id)])
        for ids in exist_leave_detail_ids:
            exist_leave_detail_ids.unlink()

        # Current Year Leaves Allocation
        last_date_format = datetime.strptime(self.last_working_date, '%Y-%m-%d')
        last_working_year = last_date_format.year
        current_year_allocation = 0
        self.env.cr.execute("""select sum(number_of_days) from hr_holidays where employee_id=%s and type='add' 
                                and year=(select id from hr_year where year='%s')
                                and state='validate' and name not like %s and 
                                holiday_status_id=(select id from hr_holidays_status where is_annual_leave=True)""",
                            [self.employee_id.id,last_working_year,'%carried%'])
        current_year_allocation = self.env.cr.fetchone()[0] or 0

        leave_line_obj.create({'gratuity_id': self.id,
                               'name': 'Current Year Leaves Allocation',
                               'days': current_year_allocation})

        # Carry forward from Last Year
        prev_year_carry = 0
        self.env.cr.execute("""select sum(number_of_days) from hr_holidays where employee_id=%s and type='add' 
                                        and year=(select id from hr_year where year='%s')
                                        and state='validate' and name like %s and 
                                        holiday_status_id=(select id from hr_holidays_status where is_annual_leave=True)""",
                            [self.employee_id.id, last_working_year, '%carried%'])
        prev_year_carry = self.env.cr.fetchone()[0] or 0

        leave_line_obj.create({'gratuity_id': self.id,
                               'name': 'Previous Year Carry Forward',
                               'days': prev_year_carry})

        # Leaves taken Current Year
        current_year_leaves = 0
        self.env.cr.execute("""select abs(sum(number_of_days)) from hr_holidays where employee_id=%s and type='remove' 
                                                and year=(select id from hr_year where year='%s')
                                                and state='validate' and 
                                                holiday_status_id=(select id from hr_holidays_status where is_annual_leave=True)""",
                            [self.employee_id.id, last_working_year])
        current_year_leaves = self.env.cr.fetchone()[0] or 0

        leave_line_obj.create({'gratuity_id': self.id,
                               'name': 'Leaves Taken',
                               'days': current_year_leaves})

        # Leave eligibility until last working date
        leave_eligible = 0
        last_working_month = last_date_format.month
        leave_eligible = round((current_year_allocation / 12) * (last_working_month - 1))

        leave_line_obj.create({'gratuity_id': self.id,
                               'name': 'Leave Eligibility until Last working day',
                               'days': leave_eligible})

        # Leave eligibility for encashment
        leave_encash = 0
        leave_encash = leave_eligible - current_year_leaves + prev_year_carry

        leave_line_obj.create({'gratuity_id': self.id,
                               'name': 'Leave Eligibility for Encashment',
                               'days': leave_encash})

        #leaves_per_day_basic = leaves_remaining * per_day_basic
        leaves_per_day_basic = leave_encash * per_day_gross

        # Write Leave details into Extra lines
        gratuity_extra_ids = self.env['hr.gratuity.extra'].search([('gratuity_id','=',self.id)])
        for ids in gratuity_extra_ids:
            gratuity_extra_ids.unlink()
        gratuity_extra_object = self.env['hr.gratuity.extra']
        gratuity_extra_object.create({
                'gratuity_id': self.id,
                'name': 'Leave encashment for ' +  str(leave_encash) + ' days',
                'amount': leaves_per_day_basic,
                }
            )

        # Calculate Total EoS Payment
        self._get_values()
        return True


    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    unlink
    # Description    :    Block deletion of records not in draft state
    #===============================================================================
    @api.multi
    def unlink(self):
        for rec in self.browse(self.id):
            if rec.state != 'draft':
                raise UserError(_('You can only delete draft records!'))
        return super(hr_gratuity, self).unlink()

    # ===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_submit (Button)
    # Description    :    Mark the record as Waiting
    # ===============================================================================
    @api.multi
    def button_submit(self):
        self.write({'state': 'waiting'})
        return True

    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_approve (Button)
    # Description    :    Mark the record as Approved
    #===============================================================================
    @api.multi
    def button_approve(self):
        self.write({'state': 'approved',
                    'approved_id': self.env.user.id})
        return True

    # ===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_reject (Button)
    # Description    :    Mark the record as Draft
    # ===============================================================================
    @api.multi
    def button_reject(self):
        self.write({'state': 'draft'})
        return True
    
    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_cancel (Button)
    # Description    :    Cancel the record
    #===============================================================================
    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancelled'})
        return True
    
    #===============================================================================
    # Class          :    hr_gratuity
    # Method         :    button_reset (Button)
    # Description    :    Reset the record to Draft
    #===============================================================================
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True


#=====================================================
# Gratuity split up details
#=====================================================
class hr_gratuity_line(models.Model):
    _name = 'hr.gratuity.line'    
 
    gratuity_id= fields.Many2one('hr.gratuity', string='Gratuity')
    contract_id= fields.Many2one('hr.contract', string='Contract')
    date_from= fields.Date('From Date')
    date_to= fields.Date('To Date')
    total_days= fields.Integer(string='Total Days')
    amount= fields.Float(string='Gratuity Amount (AED)')
     

#=====================================================
# Gratuity: Additional components
#=====================================================
class hr_gratuity_extra(models.Model):
    _name = 'hr.gratuity.extra'   
    
    gratuity_id= fields.Many2one('hr.gratuity', string='Gratuity')
    name= fields.Text(string='Description')
    amount= fields.Float(string='Amount (AED)', digits=(16,2))


# =====================================================
# Salary Details
# =====================================================
class hr_gratuity_salary_details(models.Model):
    _name = 'hr.gratuity.salary.details'

    gratuity_id = fields.Many2one('hr.gratuity', string='Gratuity')
    name = fields.Text(string='Salary Component')
    monthly = fields.Float(string='Monthly Amount (AED)')
    daily = fields.Float(string='Daily Amount (AED)')

# =====================================================
# Leave Details
# =====================================================
class hr_gratuity_leave_details(models.Model):
    _name = 'hr.gratuity.leave.details'

    gratuity_id = fields.Many2one('hr.gratuity', string='Gratuity')
    name = fields.Text(string='Description')
    days = fields.Float(string='Days')
