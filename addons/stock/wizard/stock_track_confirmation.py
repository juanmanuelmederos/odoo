# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools


class StockTrackConfirmation(models.TransientModel):
    _name = 'stock.track.confirmation'

    @api.model
    def default_get(self, fields):
        res = super(StockTrackConfirmation, self).default_get(fields)
        inventory = self.env['stock.inventory'].browse(self._context['active_id'])
        inventory_lines = inventory.mapped('line_ids').filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id)
        data = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
        res['tracking_line_ids'] = data
        return res

    tracking_line_ids = fields.One2many('stock.track.line', 'wizard_id')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')

    @api.one
    def action_confirm(self):
        return self.inventory_id._action_done()

class StockTrackingLines(models.TransientModel):
    _name = 'stock.track.line'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    tracking = fields.Selection([('lot', 'Tracked by lot'), ('serial', 'Tracked by serial number')], readonly=True)
    wizard_id = fields.Many2one('stock.track.confirmation', readonly=True)
