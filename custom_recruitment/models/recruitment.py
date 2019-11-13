# -*- coding: utf-8 -*-
##############################################################################
#    Author: Sreekanth
#    Copyright 2018 ELCA Systems
##############################################################################

from odoo import models,fields,api, _
from odoo.exceptions import UserError, AccessError, ValidationError

# ==============================================
# HR Applicant (Recruitment form) - Inheritance
# ==============================================
class Applicant(models.Model):
    _inherit = 'hr.applicant'

    cv_receipt_date = fields.Date('CV Receipt Date')
    cv_recipient_id = fields.Many2one('res.users', string='CV Recipient', default=lambda self: self.env.user)
    hiring_area_ids = fields.Many2many('hr.department', string='Potential Hiring Areas')
    assesment_potential = fields.Text('Assessment Potential')
    asses_potential_id = fields.Many2one('asses.potential.master', 'Potential')
    assesment_personality = fields.Text('Assessment Personality')
    assesment_qualification = fields.Text('Assessment Qualification')
    asses_qualification_id = fields.Many2one('asses.qualification.master', 'Qualification')
    assesment_leadership = fields.Text('Assessment Leadership')
    asses_leadership_id = fields.Many2one('asses.leadership.master', 'Leadership')
    cv_source_id = fields.Many2one('cv.source.master', 'CV Source')
    salary_expected_extra_ids = fields.Many2many('salary.extra.expected.master', string='Expected Salary Advantages')
    salary_proposed_extra_ids = fields.Many2many('salary.extra.proposed.master', string='Proposed Salary Advantages')

class AssesmentPotentialMaster(models.Model):
    _name = 'asses.potential.master'
    name = fields.Char('Potential')

class AssesmentQualificationMaster(models.Model):
    _name = 'asses.qualification.master'
    name = fields.Char('Qualification')

class AssesmentLeadershipMaster(models.Model):
    _name = 'asses.leadership.master'
    name = fields.Char('Leadership')

class CVSourceMaster(models.Model):
    _name = 'cv.source.master'
    name = fields.Char('CV Source')

class SalExtraExpectedMaster(models.Model):
    _name = 'salary.extra.expected.master'
    name = fields.Char('Extra Salary Advantage')

class SalExtraProposedMaster(models.Model):
    _name = 'salary.extra.proposed.master'
    name = fields.Char('Extra Salary Advantage')
