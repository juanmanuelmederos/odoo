# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductReplenish(models.TransientModel):
    _name = 'product.replenish'

    product_id = fields.Many2one('product.product', string='Product')
    product_tmpl_id = fields.Many2one('product.template', String='Product Template')
    product_has_variants = fields.Boolean('Has variants', default=False)
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unity of measure')
    quantity = fields.Integer('Quantity', default=1)
    date_planned = fields.Date('Scheduled Date')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_view_location_id = fields.Many2one('stock.location', related='warehouse_id.view_location_id')
    location_id = fields.Many2one('stock.location', 'Location to Replenish', required=True)
    route_ids = fields.Many2many('stock.location.route', string='Apply Specific Route(s)',
        help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,...")

    @api.model
    def default_get(self, fields):
        res = super(ProductReplenish, self).default_get(fields)
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        product_id = False
        product_tmpl_id = False
        if 'product_id' in fields:
            if self.env.context.get('default_product_id'):
                product_id = self.env['product.product'].browse(self.env.context['default_product_id'])
                res['product_tmpl_id'] = product_id.product_tmpl_id.id
                res['product_id'] = product_id.id
            elif self.env.context.get('default_product_tmpl_id'):
                product_tmpl_id = self.env['product.template'].browse(self.env.context['default_product_tmpl_id'])
                res['product_tmpl_id'] = product_tmpl_id.id
                res['product_id'] = product_tmpl_id.product_variant_ids.ids[0]
                if len(product_tmpl_id.product_variant_ids) > 1:
                    res['product_has_variants'] = True 
        if 'product_uom_id' in fields:
            if product_id:
                res['product_uom_id'] =  product_id.uom_id.id
            elif product_tmpl_id:
                res['product_uom_id'] =  product_tmpl_id.uom_id.id
        if 'warehouse_id' in fields:
            if warehouse:
                res['warehouse_id'] = warehouse.id
        if 'location_id' in fields and not res.get('location_id'):
            if warehouse:
                res['location_id'] = warehouse.lot_stock_id.id
        return res

    @api.onchange('warehouse_id')
    def _on_change_warehouse_id(self):
        self.location_id = self.warehouse_id.lot_stock_id.id
        return {'domain': {'location_id': [('usage', '=', 'internal'), ('id', 'child_of', [self.warehouse_view_location_id.id])]}}

    def launch_replenishment(self):
        replenishment = self.env['procurement.group'].create({
            'partner_id': self.product_id.responsible_id.partner_id.id,
        })
        errors = []
        try:
            self.env['procurement.group'].run(
                self.product_id,
                self.quantity,
                self.product_uom_id,
                self.location_id,
                "Manual Replenishment", # Name
                "Manual Replenishment", # Origin
                # Values
                {
                    'warehouse_id': self.warehouse_id,
                    'route_ids': self.route_ids,
                    'date_planned': self.date_planned and self.date_planned or fields.Datetime.now(),
                    'group_id': replenishment,
                }
            )

        except UserError as error:
            errors.append(error.name)

        if errors:
            raise UserError('\n'.join(errors))
