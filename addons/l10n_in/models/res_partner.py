# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    country_code = fields.Char(related="country_id.code",string="Country code")
    is_e_commerce = fields.Boolean("E-Commerce", help="Tick this to define E-Commerce partner")
