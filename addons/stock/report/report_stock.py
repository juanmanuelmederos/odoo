# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockPickingOperations(models.AbstractModel):
    _name = 'report.stock.report_picking'

    @api.multi
    def get_report_values(self, docids, data=None):
        picking = self.env['stock.picking'].browse(docids)
        picking.write({'printed': True})
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': picking,
            'data': data,
        }
