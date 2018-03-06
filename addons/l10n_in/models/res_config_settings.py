# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.iap import jsonrpc

DEFAULT_ENDPOINT = 'http://localhost:8070'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_in_b2cs_max_amount = fields.Float(string="B2CS Max amount", default=250000, config_parameter='l10n_in.l10n_in_b2cs_max_amount')
    register_gstn_service = fields.Boolean(string="Register GSTN Service", related="company_id.register_gstn_service")

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env.ref('l10n_in.ir_cron_gstr_upload_scheduler_action').sudo().write({'active': self.register_gstn_service})
        if self.register_gstn_service:
            IrParams = self.env['ir.config_parameter'].sudo()
            if not IrParams.get_param('register.gstn.service.%s'%(self.env.user.company_id.id)):
                user_token = self.env['iap.account'].get('gst_return_sandbox')
                default_sale_tax_rate = 18
                if self.env.user.company_id.account_sale_tax_id.tax_group_id.id in self.env['account.invoice.gst.report'].get_all_gst_groups():
                    default_sale_tax_rate = self.env.user.company_id.account_sale_tax_id.amount
                params = {
                    'account_token': user_token.account_token,
                    'server_version': odoo.release.version,
                    'db': self.env.cr.dbname,
                    'company_name': self.env.user.company_id.name,
                    'company_email': self.env.user.company_id.email,
                    'company_gstn': self.env.user.company_id.vat,
                    'url': IrParams.get_param('web.base.url'),
                    'dbuuid':IrParams.get_param('database.uuid'),
                    'default_sale_tax_rate': default_sale_tax_rate,
                }
                if not params.get('company_email', False):
                    raise ValidationError("Company email is not set. First set company email")
                if not params.get('company_gstn', False):
                    raise ValidationError("Company GSTN is not set. First set Company GSTN")
                # ir.config_parameter allows locally overriding the endpoint
                # for testing & al
                endpoint = IrParams.get_param('gst_return_sandbox.endpoint', DEFAULT_ENDPOINT)
                jsonrpc(endpoint + '/gstr_return/register_user', params=params)
                IrParams.set_param('register.gstn.service.%s'%(self.env.user.company_id.id), True)
