# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.tools.float_utils import float_round, float_is_zero


class ResCompany(models.Model):
    _inherit = "res.company"

    register_gst_service = fields.Boolean(string="Register GSTN Service")
