# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def web_dashboard_create_users(self, emails):

        # Reactivate already existing users if needed
        deactivated_users = self.with_context(active_test=False).search([('active', '=', False), '|', ('login', 'in', emails), ('email', 'in', emails)])
        for user in deactivated_users:
            user.active = True

        new_emails = set(emails) - set(deactivated_users.mapped('email'))
        return self.web_dashboard_create_new_users(list(new_emails))

    @api.model
    def web_dashboard_create_new_users(self, new_emails):
        # Process new email addresses : create new users
        for email in new_emails:
            default_values = {'login': email, 'name': email.split('@')[0], 'email': email, 'active': True}
            self.with_context(signup_valid=True).create(default_values)
        return True
