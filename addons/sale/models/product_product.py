# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _sales_count(self):
        r = {}
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('product_id', 'in', self.ids),
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            product.sales_count = r.get(product.id, 0)
        return r

    sales_count = fields.Integer(compute='_sales_count', string='# Sales', help="Sales in past 365 days")

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
            'context': {'group_by': ['date_order', 'state'], 'graph_measure': 'amount_untaxed',}
        }
