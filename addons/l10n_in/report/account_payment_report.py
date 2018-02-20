# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models

class AccountPaymentReport(models.Model):

    _name = "account.payment.report"
    _description = "Payment Analysis"
    _auto = False
    _rec_name = 'payment_date'

    payment_id = fields.Integer('Payment Id')
    payment_date = fields.Date('Payment Date')
    state_code = fields.Char("State Code")
    amount = fields.Float(string="Advance Payment Amount")
    invoice_date = fields.Date(string="Invoice Date")
    invoice_number = fields.Char(string="Invoice Number")
    invoice_payment = fields.Float(string="Invoice Payment")
    partner_gstn = fields.Char(string="Parnter GSTN")
    company_gstn = fields.Char(string='Company GSTN')
    date_maturity = fields.Date(string='Due date')
    #    help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    amount_residual = fields.Float()
    internal_type = fields.Selection([('payable', 'Payable'), ('receivable', 'Receivable')], string="Internal Type")
    unreconcile = fields.Boolean("Unreconcile")
    company_id = fields.Integer("Company")

    _depends = {
        'account.invoice': [
            'commercial_partner_id', 'company_id', 'state', 'type',
        ],
        'account.payment': [
            'invoice_ids', 'amount', 'payment_date'
        ],
        'account.move.line': ['payment_id'],
        'res.partner': ['country_id', 'state_id'],
    }

    def _select(self):
        select_str = """
            SELECT row_number() OVER() AS id,
                   ap.id as payment_id,
                   ap.payment_date as payment_date,
                   ap.company_id as company_id,
                   rcs.l10n_in_tin as state_code,
                   ai.number as invoice_number,
                   sum(apr.amount) as invoice_payment,
                   ap.amount as amount,
                   aml.amount_residual as amount_residual,
                   aml.date_maturity as date_maturity,
                   ai.date_invoice as invoice_date,
                   p.vat as partner_gstn,
                   apcp.vat as company_gstn,
                   acc.internal_type as internal_type,
                   aml.reconciled as reconciled,
                   CASE WHEN aml.full_reconcile_id IS NULL then true else false END as unreconcile
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_payment ap
                JOIN res_company apc ON apc.id = ap.company_id
                JOIN res_partner apcp ON apcp.id = apc.partner_id
                JOIN res_partner p ON p.id = ap.partner_id
                LEFT JOIN res_country_state rcs ON  rcs.id = p.state_id
                JOIN account_move_line aml ON aml.payment_id = ap.id
                JOIN account_account acc ON acc.id = aml.account_id AND acc.internal_type IN ('payable', 'receivable')
                LEFT JOIN account_partial_reconcile apr
                    ON CASE WHEN  acc.internal_type = 'receivable'
                        THEN
                            apr.credit_move_id = aml.id
                        ELSE
                            apr.debit_move_id = aml.id
                        END
                LEFT JOIN account_move_line ai_aml
                    ON CASE WHEN  acc.internal_type = 'receivable'
                        THEN
                            ai_aml.id = apr.debit_move_id
                        ELSE
                            ai_aml.id = apr.credit_move_id
                        END
                LEFT JOIN account_invoice ai ON ai.id = ai_aml.invoice_id
                where ap.state = ANY (ARRAY['posted','sent','reconciled']) and apc.register_gstn_service = True
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ap.id,
                        ap.amount,
                        ap.company_id,
                        ap.payment_date,
                        ai.date_invoice,
                        p.state_id,
                        rcs.l10n_in_tin,
                        p.vat,
                        apcp.vat,
                        aml.reconciled,
                        aml.date_maturity,
                        acc.internal_type,
                        aml.reconciled,
                        aml.full_reconcile_id,
                        ai.number,
                        aml.amount_residual
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
