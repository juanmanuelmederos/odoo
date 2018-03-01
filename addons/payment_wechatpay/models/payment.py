# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid
import requests
import io
import base64

from hashlib import md5
from werkzeug import urls
from lxml import etree

from odoo import api, fields, models
from odoo.addons.payment_wechatpay.controllers.main import WeChatPayController
from odoo.exceptions import UserError

try:
    import qrcode
except ImportError:
    qrcode = None

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('wechatpay', 'WeChat Pay')])
    wechatpay_appid = fields.Char(
        string='Application ID', required_if_provider='wechatpay', groups='base.group_user',
        help='The Application ID is used to ensure communications coming from WeChat Pay are valid and secured.')
    wechatpay_mch_id = fields.Char(
        string='Merchant ID', required_if_provider='wechatpay', groups='base.group_user')
    wechatpay_app_key = fields.Char(string='Application Key', required_if_provider='wechatpay', groups='base.group_user')

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * md5 decryption : support saving payment data by md5 decryption
        """
        res = super(PaymentAcquirer, self)._get_feature_support()
        res['fees'].append('wechatpay')
        return res

    @api.model
    def _get_wechatpay_urls(self, environment):
        """ Wechat Pay URLS """
        return 'https://api.mch.weixin.qq.com/pay/unifiedorder'

    @api.multi
    def wechatpay_compute_fees(self, amount, currency_id, country_id):
        """ Compute Wechat Pay fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        fees = 0.0
        if self.fees_active:
            country = self.env['res.country'].browse(country_id)
            if country and self.company_id.country_id.id == country.id:
                percentage = self.fees_dom_var
                fixed = self.fees_dom_fixed
            else:
                percentage = self.fees_int_var
                fixed = self.fees_int_fixed
            fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    def get_trade_no(self):
        return str(uuid.uuid4()).replace('-', '')

    def dict2xml(self, data, xml=''):
        for key, value in data.items():
            xml += '<%s>%s</%s>' % (key, str(value), key)
        return '<xml>' + xml + '</xml>'

    @api.multi
    def build_sign(self, val):
        data_string = '&'.join(["{}={}".format(k, v) for k, v in sorted(val.items()) if k not in ['sign', 'sign_type', 'reference']]) + '&key=' + self.wechatpay_app_key
        return md5(data_string.encode('utf-8')).hexdigest()

    @api.multi
    def _generate_qr_code(self, text):
        qr_code = qrcode.QRCode(version=4, box_size=4, border=1)
        qr_code.add_data(text)
        qr_code.make(fit=True)
        qr_img = qr_code.make_image()
        output = io.BytesIO()
        qr_img.save(output, format='JPEG')
        return base64.b64encode(output.getvalue())

    @api.multi
    def _get_wechatpay_tx_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        tx = self.env['payment.transaction'].search([('reference', '=', values.get('reference'))], limit=1)
        wechatpay_tx_values = ({
            'appid': self.wechatpay_appid,
            'mch_id': self.wechatpay_mch_id,
            'device_info': '180.211.100.4',
            'nonce_str': self.get_trade_no(),
            'body': values.get('reference'),
            'out_trade_no': tx.out_trade_no or self.get_trade_no(),
            'total_fee': int((values.get('amount') + values.get('fees')) * 100),
            'fee_type': 'GBP',
            'spbill_create_ip': '180.211.100.4',
            'notify_url': urls.url_join(base_url, WeChatPayController._notify_url) + "?redirect_url=" + str(values.get('return_url')),
            'trade_type': 'NATIVE',
        })
        wechatpay_tx_values['sign'] = self.build_sign(wechatpay_tx_values).upper()
        resp = requests.post(self._get_wechatpay_urls(self.environment), self.dict2xml(wechatpay_tx_values))
        resp_data = etree.fromstring(resp.text)
        if resp_data.find('return_msg').text == 'OK':
            attachment = self.env['ir.attachment'].search([('name', '=', 'wechatpay ' + str(values.get('reference')))])
            if attachment:
                attachment.write({'datas': self._generate_qr_code(resp_data.find('code_url').text)})
            else:
                attachment.create({
                    'name': 'wechatpay ' + str(values.get('reference')),
                    'datas': self._generate_qr_code(resp_data.find('code_url').text),
                    'res_model': tx._name,
                    })
            tx.write({
                'out_trade_no': wechatpay_tx_values.get('out_trade_no')
                })
        else:
            raise UserError(resp_data.find('return_msg').text)
        return wechatpay_tx_values

    @api.multi
    def wechatpay_form_generate_values(self, values):
        values.update(self._get_wechatpay_tx_values(values))
        return values

    @api.multi
    def wechatpay_get_form_action_url(self):
        return self._get_wechatpay_urls(self.environment)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    out_trade_no = fields.Char(string='Trade Number', readonly=True)
    provider = fields.Selection(related='acquirer_id.provider')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _wechatpay_form_get_tx_from_data(self, data):
        return

    @api.multi
    def _wechatpay_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        return invalid_parameters

    @api.multi
    def _wechatpay_form_validate(self, data):
        return
