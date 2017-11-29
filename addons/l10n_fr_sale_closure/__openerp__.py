# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Certification CGI 286 I-3 bis - Sale Closures',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This module adds support for automatic sales closings with computation of both period and cumulative totals (daily, monthly, annually)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The module adds following features:

    Storage: automatic sales closings with computation of both period and cumulative totals (daily, monthly, annually)

""",
    'depends': ['l10n_fr_certification'],
    'installable': True,
    'auto_install': True,
    'application': False,
    'data': [
        'views/account_sale_closure.xml',
        'data/account_sale_closure_cron.xml',
        'security/ir.model.access.csv'
    ],
    'post_init_hook': '_setup_inalterability',
}
