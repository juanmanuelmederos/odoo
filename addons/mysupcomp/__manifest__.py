# -*- coding: utf-8 -*-
{
    'name': "My SuperComputer Inc.",

    'summary': """
        MSCI Management Module""",

    'description': """
        Manage sales & commissions, schedule meetings....
    """,

    'author': "Odoo",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Training',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'sale', 'crm'],

    # always loaded
    'data': [
        "views/menus.xml",
        "views/product.xml",
    ],
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
}
