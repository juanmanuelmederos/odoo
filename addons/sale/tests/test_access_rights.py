# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import Form, tagged
from .test_sale_common import TestCommonSaleNoChart


@tagged('post_install', '-at_install')
class TestAccessRights(TestCommonSaleNoChart):

    def setUp(self):
        super(TestAccessRights, self).setUp()
        group_user = self.env.ref('sales_team.group_sale_salesman')
        # Create a users
        self.user_manager = self.env['res.users'].create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'email': 'a.m@example.com',
            'signature': '--\nAndreww',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_manager').id])]
        })
        self.user_salesperson = self.env['res.users'].create({
            'name': 'Mark User',
            'login': 'user',
            'email': 'm.u@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_user.id])]
        })
        self.user_salesperson_1 = self.env['res.users'].create({
            'name': 'Noemie User',
            'login': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_user.id])]
        })
        self.user_portal = self.env['res.users'].create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'signature': 'SignChell',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })
        self.user_employee = self.env['res.users'].create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notification_type': 'email',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

        # Create the SO
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'user_id': self.user_salesperson.id
        })

    def test_access_sales_manager(self):
        """ Test sales manager's access rights """
        # Manager can see the SO of other salesperson
        self.order.sudo(self.user_manager).read
        # Manager can create the SO of other salesperson
        sale_order = self.env['sale.order'].sudo(self.user_manager).create({
            'partner_id': self.partner_customer_usd.id,
            'user_id': self.user_salesperson_1.id
        })
        self.assertIn(sale_order.id, self.env['sale.order'].search([]).ids, 'Sales manager should be able to create the SO of other salesperson')

        # Manager can change a salesperson of the SO
        with Form(sale_order) as order:
            order.user_id = self.user_salesperson
        # Manager can delete the SO of other salesperson
        sale_order.unlink()
        self.assertNotIn(sale_order.id, self.env['sale.order'].search([]).ids, 'Sales manager should be able to delete the SO')

        # Manager can create a sales channel
        india_channel = self.env['crm.team'].sudo(self.user_manager).create({
            'name': 'India',
        })
        self.assertIn(india_channel.id, self.env['crm.team'].search([]).ids, 'Sales manager should be able to create a sales channel')
        # Manager can edit a sales channel
        with Form(india_channel) as team:
            team.dashboard_graph_group = 'week'
        self.assertEquals(india_channel.dashboard_graph_group, 'week', 'Sales manager should be able to edit a sales channel')
        # Manager can delete a sales channel
        india_channel.unlink()
        self.assertNotIn(india_channel.id, self.env['crm.team'].search([]).ids, 'Sales manager should be able to delete a sales channel')

    def test_access_sales_person(self):
        """ Test Salesperson's access rights """
        # Salesperson can see only his/her sale order
        self.assertRaises(AccessError, self.order.sudo(self.user_salesperson_1).read, ['user_id'])

        # Salesperson cann't create the SO of other salesperson
        with self.assertRaises(AccessError):
            self.env['sale.order'].sudo(self.user_salesperson_1).create({
                'partner_id': self.partner_customer_usd.id,
                'user_id': self.user_salesperson.id
            })

        # Now assign SO to himself/herself
        sale_order_1 = self.env['sale.order'].sudo(self.user_salesperson_1).create({
            'partner_id': self.partner_customer_usd.id,
        })
        # Salesperson cann't delete the SO
        with self.assertRaises(AccessError):
            sale_order_1.unlink()

        # Salesperson can see a sales channel
        sale_order_1.team_id.read
        # Salesperson can change a sales channel of SO
        with Form(sale_order_1) as order:
            order.team_id = self.env.ref('sales_team.crm_team_1')

    def test_access_portal_user(self):
        """ Test portal user's access rights """
        # Portal user can see the SO for which he/she is assigned as customer
        self.assertRaises(AccessError, self.order.sudo(self.user_portal).read, ['user_id'])
        with Form(self.order) as o:
            o.partner_id = self.user_portal.partner_id
        # Portal user can see the SO for which he/she is assigned as customer and also SO in 'sale' state
        self.assertRaises(AccessError, self.order.sudo(self.user_portal).read, ['user_id'])
        self.order.action_confirm()
        self.assertEquals(self.order.state, 'sale', 'Sale order should be in "sale" state')
        self.order.sudo(self.user_portal).read

    def test_access_employee(self):
        """ Test classic employee's access rights """
        # Employee cann't able to see any features of sales module
        self.assertRaises(AccessError, self.order.sudo(self.user_employee).read, ['user_id'])
