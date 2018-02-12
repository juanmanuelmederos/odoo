# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Stock',
    'version': '1.2',
    'category': 'Purchases',
    'sequence': 60,
    'summary': 'Purchase Orders, Receipts, Vendor Bills for Stock',
    'description': "",
    'website': 'https://www.odoo.com/page/purchase',
    'depends': ['stock_account', 'purchase'],
    'data': [
        'data/purchase_stock_data.xml',
        'views/stock_views.xml',
        'report/purchase_report_views.xml',
        'report/purchase_report_templates.xml',
    ],
    'demo': [
        'data/purchase_stock_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}
