from odoo import models, fields, api, exceptions, _

class SaleOrder(models.Model):

    _inherit = 'sale.order'

    commission = fields.Monetary(string='Commission', compute='_compute_commission_sale_order')

    @api.depends('order_line')
    def _compute_commission_sale_order(self):
        commission = 0
        for order in self:
            for order_line in order.order_line:
                order.commission += order_line.commission


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    commission = fields.Monetary(string='Commission', compute='_compute_commission',store=True)

    def _compute_commission(self):
        for order_line in self:
            commission_percentage = order_line.product_id.categ_id.commission_percentage
            if commission_percentage == 0:
                commission_percentage = order_line.product_id.categ_id.parent_id.commission_percentage
            order_line.commission = ( commission_percentage / 100 ) * order_line.price_total
