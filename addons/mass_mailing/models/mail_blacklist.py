# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.blacklist'
    _description = 'Mail Blacklist'

    name = fields.Char(string='Name', required=True)
    blacklist_date = fields.Date(string='Blacklist Date', default=fields.Date.context_today)
    email = fields.Char(string='Email Address', required=True)
    company_name = fields.Char(string='Company Name')

    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]
