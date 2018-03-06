# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_sale_total = fields.Boolean(string='Sales')
    kpi_sale_total_value = fields.Monetary(compute='_compute_kpi_sale_total_value')

    @api.depends('start_date', 'end_date')
    def _compute_kpi_sale_total_value(self):
        context = self._context
        for record in self:
            date_domain = [("date_order", ">=", record.start_date), ("date_order", "<=", record.end_date)]
            if context.get('timeframe') == 'yesterday':
                date_domain = [("date_order", ">=", record.start_date), ("date_order", "<", record.end_date)]
            date_domain += [('state', 'not in', ['draft', 'cancel', 'sent']), ('company_id', '=', context.get('company_id').id)]
            confirmed_sales = self.env['sale.order'].read_group(date_domain, ['amount_total'], ['amount_total'])
            record.kpi_sale_total_value = sum([confirmed_sale['amount_total'] for confirmed_sale in confirmed_sales])
