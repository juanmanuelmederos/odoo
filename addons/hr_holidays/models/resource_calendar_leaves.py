# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import api, fields, models


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    leave_ids = fields.One2many('hr.leave', 'calendar_leave_id')

    @api.model
    def create(self, values):
        result = super(ResourceCalendarLeaves, self).create(values)
        if values.get('time_type', 'leave') in ['leave', 'other'] and not values.get('resource_id', False):
            self.create_leaves(values)
        return result

    def write(self, values):
        res = super(ResourceCalendarLeaves, self).write(values)
        if not self.resource_id:
            date_from = values.get('date_from', self.date_from)
            date_to = values.get('date_to', self.date_to)
            if isinstance(date_from, str):
                date_from = fields.Datetime.from_string(date_from)
            if isinstance(date_to, str):
                date_to = fields.Datetime.from_string(date_to)
            time_delta = date_to - date_from
            number_of_days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

            for leave in self.leave_ids:
                leave.write({
                    'name': values.get('name', self.name),
                    'holiday_status_id': values.get('company_id', self.company_id).bank_leaves_type_id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'number_of_days_temp': number_of_days,
                })
        return res

    def create_leaves(self, values={}):
        date_from = values.get('date_from', self.date_from)
        date_to = values.get('date_to', self.date_to)
        if isinstance(date_from, str):
            date_from = fields.Datetime.from_string(date_from)
        if isinstance(date_to, str):
            date_to = fields.Datetime.from_string(date_to)
        time_delta = date_to - date_from
        number_of_days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

        employees = self.env['hr.employee'].search([('resource_calendar_id', '=', values.get('calendar_id', self.calendar_id.id))])
        Leave = self.env['hr.leave'].sudo().with_context(tracking_disable=True, auto_leave_create_disable=True)

        leaves = Leave
        for employee in employees:
            company = self.env['resource.calendar'].browse(values.get('calendar_id', self.calendar_id.id)).company_id

            try:
                leaves = leaves | Leave.create({
                    'name': values.get('name', self.name),
                    'employee_id': employee.id,
                    'holiday_status_id': company.bank_leaves_type_id.id,
                    'date_from': values.get('date_from', self.date_from),
                    'date_to': values.get('date_to', self.date_to),
                    'number_of_days_temp': number_of_days,
                    'calendar_leave_id': self,
                })
            except:
                continue
        leaves.sudo().action_approve()
