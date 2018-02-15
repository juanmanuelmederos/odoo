# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class Partner(models.Model):
    _inherit = 'res.partner'

    seller = fields.Boolean('is a seller', default=False)
    commission = fields.Float('Current commission')
