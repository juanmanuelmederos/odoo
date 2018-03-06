# -*- coding:utf-8 -*-
#az Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models

class AccountPaymentReport(models.Model):

    _name = "account.payment.report"
    _description = "Payment Analysis"
    _auto = False
    _rec_name = 'payment_date'

    @api.multi
    def _get_tax_rate(self):
        default_sale_tax_rate = 18
        default_sale_tax = self.env.user.company_id.account_sale_tax_id
        if default_sale_tax.tax_group_id in [self.env.ref('l10n_in.gst_group', False),self.env.ref('l10n_in.igst_group', False)]:
            if default_sale_tax.amount_type == 'group':
                default_sale_tax_rate = 0
                for child_tax in default_sale_tax.children_tax_ids:
                    default_sale_tax_rate += child_tax.amount
            else:
                default_sale_tax_rate = default_sale_tax.amount
        for record in self:
            record.tax_rate = default_sale_tax_rate

    payment_id = fields.Integer('Payment Id')
    payment_date = fields.Date('Payment Date')
    state_code = fields.Char("State Code")
    amount = fields.Float(string="Advance Payment Amount")
    invoice_payment = fields.Float()
    invoice_date = fields.Date(string="Invoice Date")
    internal_type = fields.Selection([('payable', 'Payable'), ('receivable', 'Receivable')], string="Internal Type")
    tax_rate = fields.Float(compute="_get_tax_rate", string="Tax rate")

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
                sub.payment_id,
                sub.state_code,
                sub.payment_date,
                sub.internal_type,
                CASE WHEN to_char(sub.invoice_date, 'MM-YYYY') = to_char(sub.payment_date, 'MM-YYYY')
                    THEN max(sub.amount) - sum(sub.invoice_payment)
                    WHEN sub.invoice_date IS NULL
                    THEN max(sub.amount)
                END as amount,
                CASE WHEN to_char(sub.invoice_date, 'MM-YYYY') != to_char(sub.payment_date, 'MM-YYYY') and sub.invoice_date IS NOT NULL
                    THEN sub.invoice_date
                END as invoice_date,
                sum(sub.invoice_payment)

        """
        return select_str
    def _sub_select(self):
        sub_select_str = """
            SELECT
                   ap.id as payment_id,
                   ap.payment_date as payment_date,
                   ap.company_id as company_id,
                   (CASE WHEN rcs.l10n_in_tin IS NOT NULL THEN concat(rcs.l10n_in_tin,'-',rcs.name) ELSE '' END) as state_code,
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
        return sub_select_str

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
                where ap.state = ANY (ARRAY['posted','sent','reconciled'])
        """
        return from_str

    def _sub_group_by(self):
        sub_group_by_str = """
                GROUP BY ap.id,
                        ap.amount,
                        ap.company_id,
                        ap.payment_date,
                        ai.date_invoice,
                        p.state_id,
                        rcs.l10n_in_tin,
                        rcs.name,
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
        return sub_group_by_str

    def _group_by(self):
        group_by_str = """
                GROUP BY sub.state_code,
                    sub.payment_id,
                    sub.invoice_date,
                    sub.payment_date,
                    sub.internal_type
        """
        return group_by_str

    @api.model_cr
    def init(self):
        # self._table = account_payment_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
               %s
            FROM (%s %s %s) as sub
            %s
        )""" % (self._table, self._select(), self._sub_select(), self._from(), self._sub_group_by() , self._group_by()))
