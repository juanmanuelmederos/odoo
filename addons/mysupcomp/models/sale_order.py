from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):

    _inherit = 'sale.order'

    commission = fields.Monetary(string='Commission', compute='_compute_commission_sale_order')
    margin_price_total = fields.Monetary(string='Margin Price', compute='_compute_margin_price_total', store=True)
    is_below_margin = fields.Boolean(compute='_compute_is_below_margin')

    @api.depends('order_line')
    def _compute_commission_sale_order(self):
        for order in self:
            for order_line in order.order_line:
                order.commission += order_line.commission

    @api.depends('order_line', 'order_line.product_uom_qty')
    def _compute_margin_price_total(self):
        for order in self:
            order.margin_price = 0
            for order_line in order.order_line:
                order.margin_price_total += order_line.margin_price * order_line.product_uom_qty

    def _compute_is_below_margin(self):
        for order in self:
            if order.amount_untaxed < order.margin_price_total:
                order.is_below_margin = True
            else:
                order.is_below_margin = False


    def _action_confirm(self):
        for order in self:
            if order.amount_untaxed < order.margin_price_total and not self.env.user.has_group('sales_team.group_sale_manager'):
                raise UserError(_('You can\'t sell products below their margin price.'))
                return False
            else:
                return super(SaleOrder, self)._action_confirm()



class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    commission = fields.Monetary(string='Commission', compute='_compute_commission',store=True)
    margin_price = fields.Monetary(string='Minimal Price', compute='_compute_margin', store=True)
    margin_percentage = fields.Integer(string='Margin %', compute='_get_margin_percent')

    @api.depends('price_total')
    def _compute_commission(self):
        for order_line in self:
            commission_percentage = order_line.product_id.categ_id.commission_percentage
            if commission_percentage == 0:
                commission_percentage = order_line.product_id.categ_id.parent_id.commission_percentage
            order_line.commission = ( commission_percentage / 100 ) * order_line.price_total

    @api.depends('product_id.standard_price')
    def _compute_margin(self):
        for order_line in self:
            cost = order_line.product_id.standard_price
            margin_percentage = order_line.product_id.categ_id.margin_percentage
            if margin_percentage == 0:
                margin_percentage = order_line.product_id.categ_id.parent_id.margin_percentage
            order_line.margin_price = ((margin_percentage + 100) / 100 ) * cost

    def _get_margin_percent(self):
        for order_line in self:
            margin_percentage = order_line.product_id.categ_id.margin_percentage
            if not margin_percentage:
                margin_percentage = order_line.product_id.categ_id.parent_id.margin_percentage
            order_line.margin_percentage = margin_percentage
