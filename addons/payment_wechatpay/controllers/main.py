# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http

_logger = logging.getLogger(__name__)


class WeChatPayController(http.Controller):
    _notify_url = '/payment/wechatpay/notify'

    def _wechatpay_validate_data(self, **post):
        res = False
        return res

    @http.route('/payment/wechatpay/notify', type='http', auth='none', methods=['POST'], csrf=False)
    def wechatpay_notify(self, **post):
        """ WeChat Pay Notify """
