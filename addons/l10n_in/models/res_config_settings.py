# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models
from odoo.addons.iap import jsonrpc

DEFAULT_ENDPOINT = 'http://localhost:8070'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_in_b2cs_max_amount = fields.Float(string="B2CS Max amount", default=250000, config_parameter='l10n_in.l10n_in_b2cs_max_amount')
    register_gst_service = fields.Boolean(string="Register GSTN Service", related="company_id.register_gst_service")

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.register_gst_service:
            ir_params = self.env['ir.config_parameter'].sudo()
            user_token = self.env['iap.account'].get('gst_retrun_sandbox')
            params = {
                'account_token': user_token.account_token,
                'server_version': odoo.release.version,
                'db': self.env.cr.dbname,
                'company_name': self.env.user.company_id.name,
                'company_email': self.env.user.company_id.email,
                'company_gstn': self.env.user.company_id.vat,
                'url': ir_params.get_param('web.base.url'),
                'dbuuid':ir_params.get_param('database.uuid'),
            }
            # ir.config_parameter allows locally overriding the endpoint
            # for testing & al
            endpoint = ir_params.get_param('gst_retrun_sandbox.endpoint', DEFAULT_ENDPOINT)
            jsonrpc(endpoint + '/gstr_retrun/register_user', params=params)
            self.env.sudo().ref('ir_cron_gstr_upload_scheduler_action').write({'active':True})
