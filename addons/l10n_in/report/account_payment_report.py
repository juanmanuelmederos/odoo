# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models

class AccountPaymentReport(models.Model):

    _name = "account.payment.report"
    _description = "Payment Analysis"
    _auto = False
    _rec_name = 'payment_date'

    payment_date = fields.Date('Payment Date')
    state_code = fields.Char("State Code")
    amount = fields.Float(string="Advance Payment Amount")
    invoice_date = fields.Date(string="Invoice Date")
    invoice_number = fields.Char(string="Invoice Number")
    invoice_payment = fields.Float(string="Invoice Payment")
    partner_gstn = fields.Char(string="Parnter GSTN")
    date_maturity = fields.Date(string='Due date', index=True, required=True,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    amount_residual = fields.Float()
    internal_type = fields.Selection([('payable', 'Payable'), ('receivable', 'Receivable')], string="Internal Type")
    unreconcile = fields.Boolean()

    def _select(self):
        select_str = """
            SELECT min(ap.id) as id,
                   ap.payment_date as payment_date,
                   rcs.l10n_in_tin as state_code,
                   ai.number as invoice_number,
                   sum(ai.amount_total) as invoice_payment,
                   ap.amount as amount,
                   ai.date_invoice as invoice_date,
                   partner.vat as partner_gstn,
                   aml.date_maturity as date_maturity,
                   aml.amount_residual as amount_residual,
                   acc.internal_type as internal_type,
                   aml.reconciled as reconciled,
                   CASE WHEN aml.full_reconcile_id IS NULL then true else false END as unreconcile
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_payment ap
                join account_invoice_payment_rel ainr ON ap.id = ainr.payment_id
                JOIN account_invoice ai ON ai.id = ainr.invoice_id
                JOIN res_partner partner ON (ai.commercial_partner_id = partner.id and ap.partner_id = partner.id)
                left JOIN res_country_state rcs ON partner.state_id = rcs.id
                LEFT JOIN account_move_line aml ON ( ap.partner_id = aml.partner_id and  partner.id = aml.partner_id)
                LEFT JOIN account_account acc ON (acc.id = aml.account_id AND acc.internal_type IN ('payable', 'receivable') AND aml.reconciled = false)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ap.amount,
                        ap.payment_date,
                        ai.date_invoice,
                        partner.state_id,
                        rcs.l10n_in_tin,
                        partner.vat,
                        aml.date_maturity,
                        aml.amount_residual,
                        aml.reconciled,
                        acc.internal_type,
                        aml.reconciled,
                        aml.full_reconcile_id,
                        ai.number
        """
        return group_by_str

    @api.model_cr
    def init(self):
        # self._table = account_payment_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._group_by())
        )
