# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AnalyticLine(models.Model):

    _inherit = 'account.analytic.line'

    origin = fields.Selection(selection_add=[('timesheet', 'Timesheet')])
