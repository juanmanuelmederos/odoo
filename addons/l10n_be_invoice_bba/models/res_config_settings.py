# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_out_inv_comm = fields.Boolean(string='Structured Communication', related='company_id.use_out_inv_comm')
    out_inv_comm_type = fields.Selection(related='company_id.out_inv_comm_type', change_default=True,
        help='Select Default Communication Type for Outgoing Invoices.', default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('random', 'Random'),
        ('date', 'Based on Date'),
        ('partner_ref', 'Based on Customer Reference'),
        ], string='Communication Algorithm',
        related='company_id.out_inv_comm_algorithm',
        help="Select Algorithm to generate the Structured Communication on Outgoing Invoices.\n\n"\
        "Random : Communication number should be generated randomly.\n"\
        "Based on Date : Communication number should be generated on the basis of the invoice creation date.\n"\
        "Based On Customer Reference: Communication number should be is generated from the customer reference.")

    @api.onchange('use_out_inv_comm')
    def _onchange_use_out_inv_comm(self):
        if self.use_out_inv_comm:
            self.out_inv_comm_type = 'bba'
        else:
            self.out_inv_comm_type = 'none'
            self.out_inv_comm_algorithm = 'random'
