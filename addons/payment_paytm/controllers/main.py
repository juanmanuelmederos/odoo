# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaytmController(http.Controller):
    _return_url = '/payment/paytm/return'

    def paytm_validate_data(self, **post):
        res = False
        resp = post.get('STATUS')
        if resp:
            if resp == 'TXN_SUCCESS':
                _logger.info('Paytm: validated data')
            elif resp == 'PENDING':
                _logger.info('Paytm: Transaction Pending')
            elif resp == 'OPEN':
                _logger.info('Paytm: Transaction open')
            elif resp == 'TXN_FAILURE':
                _logger.warning('Paytm: payment Failed and closed the transaction')
            else:
                _logger.warning('Paytm: unrecognized paytm answer, received %s instead of TXN_SUCCESS/PENDING/OPEN/TXN_FAILURE')
        if post.get('ORDERID') and post.get('TXNID'):
            post['reference'] = request.env['payment.transaction'].sudo().search([('order_id', '=', post['ORDERID'])]).reference
            res = request.env['payment.transaction'].sudo().form_feedback(post, 'paytm')
        return res

    @http.route('/payment/paytm/return', type='http', auth="none", methods=['GET', 'POST'], csrf=False)
    def paytm_return(self, redirect_url=False, **post):
        _logger.info('Beginning Paytm DPN feedback with post data %s', pprint.pformat(post))
        self.paytm_validate_data(**post)
        return werkzeug.utils.redirect(redirect_url or '/')
