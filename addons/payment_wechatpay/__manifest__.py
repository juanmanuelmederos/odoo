# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WeChat Pay Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: WeChat Pay Implementation',
    'description': """WeChat Pay Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/wechatpay_views.xml',
        'views/payment_wechatpay_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
}
