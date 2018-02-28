# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_type = fields.Selection([('manual', 'Manually set quantities on order')], string='Track Service',
        help="Manually set quantities on order: Invoice based on the manually entered quantity, without creating an analytic account.\n"
             "Timesheets on contract: Invoice based on the tracked hours on the related timesheet.\n"
             "Create a task and track hours: Create a task on the sales order validation and track the work hours.",
        default='manual', oldname='track_service')
    sale_line_warn = fields.Selection(WARNING_MESSAGE, 'Sales Order Line', help=WARNING_HELP, required=True, default="no-message")
    sale_line_warn_msg = fields.Text('Message for Sales Order Line')
    expense_policy = fields.Selection(
        [('no', 'No'), ('cost', 'At cost'), ('sales_price', 'Sales price')],
        string='Re-Invoice Policy',
        default='no')

    @api.multi
    @api.depends('product_variant_ids.sales_count')
    def _sales_count(self):
        for product in self:
            product.sales_count = sum([p.sales_count for p in product.product_variant_ids])

    @api.multi
    def action_view_sales(self):
        self.ensure_one()
        action = self.env.ref('sale.action_orders')
        view_id = self.env.ref('sale.view_sale_order_graph').id

        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'target': action.target,
            'view_id': view_id,
            'views': [(view_id, 'graph')],
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'res_model': action.res_model,
            'context': "{'group_by': ['date_order', 'state']}",
        }

    sales_count = fields.Integer(compute='_sales_count', string='# Sales', help="Sales in past 365 days")
    invoice_policy = fields.Selection(
        [('order', 'Ordered quantities'),
         ('delivery', 'Delivered quantities'),
        ], string='Invoicing Policy',
        help='Ordered Quantity: Invoice based on the quantity the customer ordered.\n'
             'Delivered Quantity: Invoiced based on the quantity the vendor delivered (time or deliveries).',
        default='order')

    @api.onchange('type')
    def _onchange_type(self):
        """ Force values to stay consistent with integrity constraints """
        if self.type == 'consu':
            self.invoice_policy = 'order'
            self.service_type = 'manual'
