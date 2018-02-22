# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    @api.multi
    def compute_price(self):
        templates = self.filtered(lambda t: t.product_variant_count == 1 and t.bom_count > 0)
        return templates.mapped('product_variant_id').compute_price()


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.multi
    def compute_price(self):
        BoM = self.env['mrp.bom']
        action_rec = self.env.ref('stock_account.action_view_change_standard_price')
        action = action_rec.read([])[0]
        is_button = self.env.context.get('button', False)
        if self.filtered(lambda p: p.categ_id.property_valuation == 'real_time') and not is_button:
            raise UserError(_('The inventory valuation of some products is automated. You can only update their cost from the product form.'))

        for product in self.filtered(lambda p: p.bom_count > 0 and p.categ_id.property_cost_method == 'standard'):
            bom = BoM._bom_find(product=product)
            if bom.bom_line_ids:
                price = product._compute_hierarchy(bom.bom_line_ids, self.ids)
                if action_rec and is_button:
                    action['context'] = {'default_new_price': price}
                    return action
                else:
                    product.standard_price = price
            else:
                return action
        return True

    def _compute_hierarchy(self, bom_line_ids, product_ids):
        self.ensure_one()
        total = 0
        bom_ids = []
        for line in bom_line_ids:
            if line._skip_bom_line(self):
                continue
            bom_id = line.bom_id
            if bom_id.routing_id and bom_id not in bom_ids:
                bom_ids.append(bom_id)
                total_cost = 0.0
                for opt in bom_id.routing_id.operation_ids:
                    rounding = bom_id.product_uom_id.rounding
                    cycle_number = float_round(bom_id.product_qty / (opt.workcenter_id.capacity * bom_id.product_qty)  , precision_rounding=rounding)
                    duration_expected = (opt.workcenter_id.time_start + opt.workcenter_id.time_stop +
                        cycle_number * opt.time_cycle * 100.0 / opt.workcenter_id.time_efficiency)
                    total_cost += (duration_expected / 60) * opt.workcenter_id.costs_hour
                total += total_cost

            # Compute recursive if line has `child_line_ids`
            if line.child_line_ids and line.product_id.id in product_ids:
                child_total = line.product_id._compute_hierarchy(line.child_line_ids, product_ids)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        return bom_id.product_uom_id._compute_price(total / bom_id.product_qty, self.uom_id)
