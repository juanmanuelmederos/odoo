# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Paytm Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Paytm: Paytm Implementation',
    'description': """Paytm Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/paytm_views.xml',
        'views/payment_paytm_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
}
