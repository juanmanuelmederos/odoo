# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    commission = fields.Float(string='Commission')

    def _select(self):
        return super(SaleReport, self)._select() + ", l.commission as commission"

    def _group_by(self):
        return super(SaleReport, self)._group_by() + ", l.commission"
