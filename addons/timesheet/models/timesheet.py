# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TimesheetLine(models.Model):

    _name = 'timesheet.line'
    _inherits = {'account.analytic.line': 'analytic_line_id'}
    _order = 'date DESC'

    def _default_resource_id(self):
        return self.env['resource.resource'].search([('user_id', '=', self.env.user.id)], limit=1)

    analytic_line_id = fields.Many2one('account.analytic.line', "Analytic Line", required=True, auto_join=True, readonly=True, ondelete="cascade")
    origin = fields.Selection(string="Origin", default='timesheet', related='analytic_line_id.origin', inherited=True)
    resource_id = fields.Many2one('resource.resource', 'Employee', auto_join=True, domain=[('resource_type', '=', 'user')], required=True)
    user_id = fields.Many2one('res.users', string="User", related='resource_id.user_id')

    @api.multi
    @api.constrains('resource_id')
    def _check_resource_type(self):
        for timesheet in self:
            if timesheet.resource_id.resource_type != 'user':
                raise ValidationError(_('The resource of a timesheet must be a user.'))
