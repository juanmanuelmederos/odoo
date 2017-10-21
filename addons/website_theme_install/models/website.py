# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Website(models.Model):
    _inherit = "website"

    theme_id = fields.Many2one('ir.module.module')
