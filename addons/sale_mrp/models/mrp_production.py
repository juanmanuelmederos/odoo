# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_cancel(self):
        res = super(MrpProduction, self).action_cancel()
        if self.procurement_group_id:
            dest = self.env['stock.move'].search(['|', ('created_production_id', 'in', self.mapped('move_finished_ids').mapped('production_id').ids), ('picking_id', 'in', self.mapped('move_finished_ids').mapped('picking_id').ids)])
            created_production = dest.mapped('created_production_id')
            stock_picking_id = dest.mapped('picking_id')
            self._log_production_order_changes({self: (self.product_qty, self.product_qty)})
        return res

    def _log_production_order_changes(self, product_qty):
        def _keys_in_sorted(move):
            """ sort by picking and the responsible for the product the
            move.
            """
            return (move.picking_id.id, move.product_id.responsible_id.id)

        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_po(order_exceptions):
            order_line_ids = self.env['sale.order.line'].browse([order_line.id for order in order_exceptions.values() for order_line in order[0]])
            group_id = self.env['procurement.group'].search([('name', '=', order_line_ids.mapped('order_id').name)])
            prod_orders = self.env['mrp.production'].search([('procurement_group_id', '=', group_id.id)])
            purchase_order_ids = order_line_ids.mapped('order_id')
            move_ids = self.env['stock.move'].search([('group_id', '=', group_id.id)])
            impacted_moves = []
            for move in move_ids:
                dest = self.env['stock.move'].search(['|', ('created_production_id', 'in', move.mapped('production_id').ids), ('picking_id', 'in', move.mapped('picking_id').ids)])
                if dest:
                    impacted_moves.append(dest.id)
                    moves = self.env['stock.move'].browse(impacted_moves)
            impacted_pickings = moves.mapped('picking_id')
            values = {
                'prod_order_ids': prod_orders,
                'order_exceptions': order_exceptions.values(),
                'impacted_pickings': impacted_pickings,
            }
            return self.env.ref('sale_mrp.exception_on_mrp').render(values=values)

        group_id = self.move_raw_ids.mapped('group_id')
        sale_order = self.env['sale.order'].search([('name', '=', group_id.name)])
        if sale_order:
            for order in sale_order:
                to_log = {}
                for order_line in order.order_line:
                    to_log[order_line] = (order_line.product_uom_qty, product_qty)
                if to_log:
                    documents = self.env['stock.picking']._log_activity_get_documents(to_log, 'move_ids', 'DOWN', _keys_in_sorted, _keys_in_groupby)
                    filtered_documents = {}
                    for (parent, responsible), rendering_context in documents.items():
                        if parent._name == 'stock.picking':
                            if parent.state == 'cancel':
                                continue
                        filtered_documents[(parent, responsible)] = rendering_context
                    activity = self.env['stock.picking']._log_activity(_render_note_exception_quantity_po, filtered_documents)
        return True
