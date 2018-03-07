# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    intrastat_id = fields.Many2one('account.intrastat.code', string='Commodity Code')
