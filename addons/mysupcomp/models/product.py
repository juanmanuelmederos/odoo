# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

class Category(models.Model):
    _inherit = 'product.category'

    commission_percentage = fields.Integer('Commission %')
    margin_percentage = fields.Integer('Margin %')

class Product(models.Model):
    _inherit = 'product.product'
