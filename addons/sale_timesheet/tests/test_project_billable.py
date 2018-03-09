# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheetNoChart


class TestProjectBillable(TestCommonSaleTimesheetNoChart):
    """ This test suite provide checks for billable project, tasks transfering, ... """

    @classmethod
    def setUpClass(cls):
        super(TestProjectBillable, cls).setUpClass()
        # set up
        cls.setUpServiceProducts()

        # SO with 2 lines (ordered and delivered creating no task), and confirm it
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
        })
        cls.so_line_delivered_no_task = cls.env['sale.order.line'].create({
            'name': cls.product_delivery_timesheet1.name,
            'product_id': cls.product_delivery_timesheet1.id,
            'product_uom_qty': 10,
            'product_uom': cls.product_delivery_timesheet1.uom_id.id,
            'price_unit': cls.product_delivery_timesheet1.list_price,
            'order_id': cls.sale_order.id,
        })
        cls.so_line_ordered_no_task = cls.env['sale.order.line'].create({
            'name': cls.product_order_timesheet1.name,
            'product_id': cls.product_order_timesheet1.id,
            'product_uom_qty': 50,
            'product_uom': cls.product_order_timesheet1.uom_id.id,
            'price_unit': cls.product_order_timesheet1.list_price,
            'order_id': cls.sale_order.id,
        })
        cls.so_line_delivered_no_task.product_id_change()
        cls.so_line_ordered_no_task.product_id_change()
        cls.sale_order.action_confirm()

        # Create projects
        cls.project_billable_task = cls.env['project.project'].create({
            'name': 'Project billable per task rate',
            'allow_timesheets': True,
            'sale_line_id': cls.so_line_delivered_no_task.id,
        })
        cls.project_non_billable = cls.env['project.project'].create({
            'name': 'Project non billable',
            'allow_timesheets': True,
        })

    def test_project_billable_task_rate(self):
        """ Create task in a billable project and move it to a non billable project. """
        # create the task in a billable project
        task = self.env['project.task'].with_context(default_project_id=self.project_billable_task.id).create({
            'name': 'Conquer the world',
            'project_id': self.project_billable_task.id,
        })
        self.assertEquals(task.sale_line_id, self.so_line_delivered_no_task, "The task created in a billable project should have the same SO line as the project.")

        # transfert the task into a non billable
        task.write({
            'project_id': self.project_non_billable.id
        })
        self.assertEquals(task.sale_line_id, self.so_line_delivered_no_task, "The SO line linked to the task should not have changed bu transfering project.")

    def test_project_non_billable(self):
        """ Create task in a non billable project and move it to a billable project. """
        # create the task in a non billable project
        task = self.env['project.task'].with_context(default_project_id=self.project_non_billable.id).create({
            'name': 'Conquer the world',
            'project_id': self.project_non_billable.id,
        })
        self.assertFalse(task.sale_line_id, "The task created in a non billable project should not have a SO line.")

        # transfert the task into a non billable
        task.write({
            'project_id': self.project_billable_task.id
        })
        self.assertFalse(task.sale_line_id, "The task created in a non billable project should not have a SO line.")
