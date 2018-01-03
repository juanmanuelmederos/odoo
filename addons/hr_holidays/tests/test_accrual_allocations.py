# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase

from odoo.tests import tagged


@tagged('accrual')
class TestAccrualAllocations(TestHrHolidaysBase):
    def setUp(self):
        super(TestAccrualAllocations, self).setUp()

        # Make sure we have the rights to create, validate and delete the leaves, leave types and allocations
        self.LeaveType = self.env['hr.leave.type'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)
        self.Allocation = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)
        self.Leave = self.env['hr.leave'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.accrual_type = self.LeaveType.create({
            'name': 'accrual',
            'limit': False,
            'double_validation': False,
            'accrual': True,
        })

        self.unpaid_type = self.LeaveType.create({
            'name': 'unpaid',
            'limit': True,
            'double_validation': False,
            'unpaid': True,
        })

        self.set_employee_create_date(self.employee_emp_id, '2010-02-03 00:00:00')
        self.set_employee_create_date(self.employee_hruser_id, '2010-02-03 00:00:00')

    def set_employee_create_date(self, id, newdate):
        """ This method is a hack in order to be able to define/redefine the create_date
            of the employees.
            This is done in SQL because ORM does not allow to write onto the create_date field.
        """
        cursor = self.env['hr.employee'].browse(id)._cr
        cursor.execute("""
                       UPDATE
                       hr_employee
                       SET create_date = '%s'
                       WHERE id = %s
                       """ % (newdate, id))

    def delete_leave(self, leave):
        leave.action_refuse()
        leave.action_draft()
        leave.unlink()

    def test_accrual_base_no_leaves(self):
        alloc_0 = self.Allocation.create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_0.action_approve()

        self.Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 1, 'Employee should have been allocated one leave day')

        self.delete_leave(alloc_0)

    def test_accrual_base_leaves(self):
        alloc_0 = self.Allocation.create({
            'name': 'Accrual allocation for employee with leaves',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_0.action_approve()

        emp = self.env['hr.employee'].browse(self.employee_hruser_id)
        df = emp.resource_calendar_id._get_previous_work_day(fields.Datetime.from_string(fields.Datetime.now())).date()

        leave_0 = self.Leave.create({
            'name': 'Leave for hruser',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.unpaid_type.id,
            'date_from': datetime.combine(df, time(0, 0, 0)),
            'date_to': datetime.combine(df + relativedelta(days=1), time(0, 0, 0)),
            'number_of_days_temp': 1,
        })

        leave_0.action_approve()

        self.Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, .8, 'As employee took some unpaid leaves last week, he should be allocated only .8 days')

        self.delete_leave(alloc_0)
        self.delete_leave(leave_0)

    def test_accrual_many(self):
        # Here we just test different units and intervals
        alloc_0 = self.Allocation.create({
            'name': '1 day per 2 weeks',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 1,
            'interval_number': 2,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_1 = self.Allocation.create({
            'name': '4 hours per week',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 4,
            'interval_number': 1,
            'unit_per_interval': 'hours',
            'interval_unit': 'weeks',
        })

        alloc_2 = self.Allocation.create({
            'name': '2 day per 1 month',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 2,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'months',
        })

        alloc_3 = self.Allocation.create({
            'name': '20 days per year',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 20,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'years',
        })

        (alloc_0 | alloc_1 | alloc_2 | alloc_3).action_approve()

        self.Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 1)
        self.assertEqual(alloc_1.number_of_days, .5)
        self.assertEqual(alloc_2.number_of_days, 2)
        self.assertEqual(alloc_3.number_of_days, 20)

        self.delete_leave((alloc_0 | alloc_1 | alloc_2 | alloc_3))

    def test_accrual_new_employee(self):
        self.set_employee_create_date(self.employee_emp_id, fields.Datetime.now())

        alloc_0 = self.Allocation.create({
            'name': 'one shot one kill',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_0.action_approve()

        self.Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Employee is new he should not get any accrual leaves')

        self.delete_leave(alloc_0)

    def test_accrual_multi(self):
        alloc_0 = self.Allocation.create({
            'name': '2 days per week',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 1,
            'interval_number': 2,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_0.action_approve()

        self.Allocation._update_accrual()
        self.Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 1, 'Cron only allocates 1 days every two weeks')

        self.delete_leave(alloc_0)

    def test_accrual_validation(self):
        alloc_0 = self.Allocation.create({
            'name': '20 days per year',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days_temp': 0,
            'accrual': True,
            'number_per_interval': 20,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'years',
            'date_to': fields.Datetime.from_string('2015-02-03 00:00:00'),
        })

        alloc_0.action_approve()

        self.Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Cron validity passed, should not allocate any leave')

        self.delete_leave(alloc_0)
