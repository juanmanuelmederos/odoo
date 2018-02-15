# -*- coding: utf-8 -*-
{
    'name': "web_dashboard",
    'category': 'Hidden',
    'version': '0.1',
    'description':
        """
Odoo Dashboard View.
========================

This module defines a new type of view that can
be used to create dashboards
        """,
    'depends': ['base'],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        "static/src/xml/dashboard_view.xml",
    ],
}
