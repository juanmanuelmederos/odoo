# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class AccountInvoiceConfirm(models.TransientModel):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "account.invoice.confirm"
    _description = "Confirm the selected invoices"

    @api.multi
    def invoice_confirm(self):
        for record in self.env['account.invoice'].get_active_records():
            if record.state != 'draft':
                raise UserError(_("Selected invoice(s) cannot be confirmed as they are not in 'Draft' state."))
            record.action_invoice_open()
        return {'type': 'ir.actions.act_window_close'}
