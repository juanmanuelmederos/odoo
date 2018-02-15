# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
import logging
import dateutil.parser
import pytz

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paytm.models import checksum
from odoo.addons.payment_paytm.controllers.main import PaytmController
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('paytm', 'Paytm')])
    paytm_merchant_id = fields.Char(
        string='Merchant ID', required_if_provider='paytm', groups='base.group_user',
        help='The Merchan ID is used to ensure communications coming from Paytm are valid and secured.')
    paytm_merchant_key = fields.Char(
        string='Merchant Key', required_if_provider='paytm', groups='base.group_user',)
    paytm_industry_type_id = fields.Char(string='Industry Type', required_if_provider='paytm', groups='base.group_user')
    paytm_website = fields.Char(string='Website', required_if_provider='paytm', groups='base.group_user')

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
        res['fees'].append('paytm')
        return res

    @api.model
    def _get_paytm_urls(self, environment):
        """ Paypal URLS """
        if environment == 'prod':
            return "https://secure.paytm.in/oltp-web/processTransaction"
        else:
            return "https://pguat.paytm.com/oltp-web/processTransaction"

    @api.multi
    def paytm_compute_fees(self, amount, currency_id, country_id):
        """ Compute paytm fees.

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

    @api.multi
    def paytm_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        tx = self.env['payment.transaction'].search([('reference', '=', values.get('reference'))], limit=1)

        data_dict = {
            'MID': self.paytm_merchant_id,
            'ORDER_ID': tx.order_id or str(uuid.uuid4()),
            'TXN_AMOUNT': values['amount'],
            'CUST_ID': values.get('partner_id'),
            'INDUSTRY_TYPE_ID': self.paytm_industry_type_id,
            'WEBSITE': self.paytm_website,
            'CHANNEL_ID': 'WEB',
            'MOBILE_NO': values.get('partner_phone'),
            'EMAIL': values.get('partner_email'),
            'CALLBACK_URL': urls.url_join(base_url, PaytmController._return_url) + "?redirect_url=" + str(values.get('return_url')),
        }
        tx.write({'order_id': data_dict['ORDER_ID']})
        param_dict = data_dict
        param_dict['CHECKSUMHASH'] = checksum.generate_checksum(data_dict, self.paytm_merchant_key)
        values.update(param_dict)
        return values

    @api.multi
    def paytm_get_form_action_url(self):
        return self._get_paytm_urls(self.environment)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    order_id = fields.Char(string="Order Id", readonly=True)
    provider = fields.Selection(related='acquirer_id.provider')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _paytm_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('reference'), data.get('TXNID')
        if not reference or not txn_id:
            error_msg = _('Paytm: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Paytm: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    @api.multi
    def _paytm_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('TXNID') != self.acquirer_reference:
            invalid_parameters.append(('TXNID', data.get('TXNID'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('TXNAMOUNT', '0.0')), (self.amount + self.fees), 2) != 0:
            invalid_parameters.append(('TXNAMOUNT', data.get('TXNAMOUNT'), '%.2f' % self.amount))  # mc_gross is amount + fees
        if data.get('MID') and self.acquirer_id.paytm_merchant_id and data['MID'] != self.acquirer_id.paytm_merchant_id:
            invalid_parameters.append(('MID', data.get('MID'), self.acquirer_id.paytm_merchant_id))

        CHECKSUMHASH = data.get('CHECKSUMHASH')
        verify_checksum = checksum.verify_checksum(data, self.acquirer_id.paytm_merchant_key, CHECKSUMHASH).decode()
        if not CHECKSUMHASH or CHECKSUMHASH != verify_checksum:
            invalid_parameters.append(('CHECKSUMHASH', verify_checksum, CHECKSUMHASH))

        return invalid_parameters

    @api.multi
    def _paytm_form_validate(self, data):
        status = data.get('STATUS')
        res = {
            'acquirer_reference': data.get('TXNID'),
        }
        if status == 'TXN_SUCCESS':
            _logger.info('Validated Paytm payment for tx %s: set as done' % (self.reference))
            try:
                # dateutil and pytz don't recognize abbreviations PDT/PST
                tzinfos = {
                    'PST': -8 * 3600,
                    'PDT': -7 * 3600,
                }
                date_validate = dateutil.parser.parse(data.get('TXNDATE'), tzinfos=tzinfos).astimezone(pytz.utc)
            except:
                date_validate = fields.Datetime.now()
            res.update(state='done', date_validate=date_validate, state_message=data.get('RESPMSG'))
            return self.write(res)
        elif status == 'PENDING':
            _logger.info('Received notification for Paytm payment %s: set as pending' % (self.reference))
            res.update(state='pending', state_message=data.get('RESPMSG'))
            return self.write(res)
        elif status == 'OPEN':
            _logger.info('Received notification for Paytm payment %s: set as Draft' % (self.reference))
            res.update(state='draft', state_message=data.get('RESPMSG'))
            return self.write(res)
        else:
            error = 'Received unrecognized status for paytm payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='error', state_message=data.get('RESPMSG'))
            return self.write(res)
