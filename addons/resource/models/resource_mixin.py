# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta, timezone

from odoo import api, fields, models
from odoo.tools import float_utils
from .resource import inter, difference

class ResourceMixin(models.AbstractModel):
    _name = "resource.mixin"
    _description = 'Resource Mixin'

    resource_id = fields.Many2one(
        'resource.resource', 'Resource',
        auto_join=True, index=True, ondelete='restrict', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get(),
        index=True, related='resource_id.company_id', store=True)
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        default=lambda self: self.env['res.company']._company_default_get().resource_calendar_id,
        index=True, related='resource_id.calendar_id', store=True)

    @api.model
    def create(self, values):
        if not values.get('resource_id'):
            resource = self.env['resource.resource'].create({
                'name': values.get(self._rec_name)
            })
            values['resource_id'] = resource.id
        return super(ResourceMixin, self).create(values)

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        resource = self.resource_id.copy()
        default['resource_id'] = resource.id
        default['company_id'] = resource.company_id.id
        default['resource_calendar_id'] = resource.calendar_id.id
        return super(ResourceMixin, self).copy_data(default)

    def get_work_days_count(self, from_datetime, to_datetime, calendar=None, domain=None):
        """ Return the number of work days for the resource, taking into account
        leaves. An optional calendar can be given in case multiple calendars can
        be used on the resource. """
        return self.get_work_days_data(from_datetime, to_datetime, calendar=calendar, domain=domain)['days']

    def get_work_hours_count(self, from_datetime, to_datetime, calendar=None, domain=None):
        """ Return the number of work hours for the resource, taking into account
        leaves. An optional calendar can be given in case multiple calendars can
        be used on the resource. """
        return self.get_work_days_data(from_datetime, to_datetime, calendar=calendar, domain=domain)['hours']

    def get_work_days_data(self, from_datetime, to_datetime, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=timezone.utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=timezone.utc)

        # retrieve attendances and leaves (with one extra day margin)
        from_full = from_datetime + timedelta(days=-1)
        to_full = to_datetime + timedelta(days=1)
        attendances = calendar._attendance_intervals(from_full, to_full)
        leaves = calendar._leave_intervals(from_full, to_full, self.resource_id, domain)

        # compute actual and total hours per day
        day_hours = defaultdict(float)
        day_total = defaultdict(float)
        for start, stop in difference(attendances, leaves):
            day_total[start.date()] += (stop - start).total_seconds() / 3600
            start, stop = max(start, from_datetime), min(stop, to_datetime)
            if start < stop:
                day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        days = sum(
            float_utils.round(4 * day_hours[day] / day_total[day]) / 4
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }

    def iter_works(self, from_datetime, to_datetime, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id
        return calendar._iter_work_intervals(from_datetime, to_datetime, self.resource_id.id, domain=domain)

    def iter_work_hours_count(self, from_datetime, to_datetime, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id
        return calendar._iter_work_hours_count(from_datetime, to_datetime, self.resource_id.id, domain=domain)

    def get_leaves_day_count(self, from_datetime, to_datetime, calendar=None, domain=None):
        """ Return the number of leave days for the resource, taking into account
        attendances. An optional calendar can be given in case multiple calendars
        can be used on the resource. """
        return self.get_leaves_days_data(from_datetime, to_datetime, calendar=calendar, domain=domain)['days']

    def get_leaves_hours_count(self, from_datetime, to_datetime, calendar=None, domain=None):
        """ Return the number of leave hours for the resource, taking into account
        attendances. An optional calendar can be given in case multiple calendars can
        be used on the resource. """
        return self.get_leaves_days_data(from_datetime, to_datetime, calendar=calendar, domain=domain)['hours']

    def get_leaves_days_data(self, from_datetime, to_datetime, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=timezone.utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=timezone.utc)

        # retrieve attendances and leaves (with one extra day margin)
        from_full = from_datetime + timedelta(days=-1)
        to_full = to_datetime + timedelta(days=1)
        attendances = calendar._attendance_intervals(from_full, to_full)
        leaves = calendar._leave_intervals(from_full, to_full, self.resource_id, domain)

        # compute actual and total hours per day
        day_hours = defaultdict(float)
        day_total = defaultdict(float)
        for start, stop in inter(attendances, leaves):
            day_total[start.date()] += (stop - start).total_seconds() / 3600
            start, stop = max(start, from_datetime), min(stop, to_datetime)
            if start < stop:
                day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        days = sum(
            float_utils.round(4 * day_hours[day] / day_total[day]) / 4
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }

    def iter_leaves(self, from_datetime, to_datetime, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id
        return calendar._iter_leave_intervals(from_datetime, to_datetime, self.resource_id.id, domain=domain)

    def get_start_work_hour(self, day_dt, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id
        work_intervals = calendar._get_day_work_intervals(day_dt, resource_id=self.resource_id.id, domain=domain)
        return work_intervals and work_intervals[0][0]

    def get_end_work_hour(self, day_dt, calendar=None, domain=None):
        calendar = calendar or self.resource_calendar_id
        work_intervals = calendar._get_day_work_intervals(day_dt, resource_id=self.resource_id.id, domain=domain)
        return work_intervals and work_intervals[-1][1]

    def get_day_work_hours_count(self, day_date, calendar=None):
        calendar = calendar or self.resource_calendar_id
        attendances = calendar._get_day_attendances(day_date, False, False)
        if not attendances:
            return 0
        return sum(float(i.hour_to) - float(i.hour_from) for i in attendances)
