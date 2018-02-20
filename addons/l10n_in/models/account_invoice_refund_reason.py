# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, models, fields


class AccountInvoiceRefundReason(models.Model):

    _name = "account.invoice.refund.reason"

    code = fields.Char("Sequence Code", required=True)
    name = fields.Char("Name", required=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The Sequence Code must be unique!')
    ]

    @api.multi
    def name_get(self):
        res = []
        for reason in self:
            name = '%s - %s' % (reason.code, reason.name)
            res.append((reason.id, name))
        return res
