# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import tools
from odoo import models, fields, api
from odoo.addons.iap import jsonrpc
import json

import logging

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'http://localhost:8070'

class AccountInvoiceGstReport(models.Model):
    _name = "account.invoice.gst.report"
    _description = "Invoices Statistics"
    _auto = False

    @api.multi
    def _get_cess_amount(self):
        for record in self:
            cess_amount_count = 0
            account_invoice_lines = self.env['account.invoice.line'].browse(eval(record.invoice_line_ids))
            for account_invoice_line in account_invoice_lines:
                price_unit = account_invoice_line.price_unit * (1 - (account_invoice_line.discount or 0.0) / 100.0)
                tax_lines = account_invoice_line.invoice_line_tax_ids.compute_all(price_unit, account_invoice_line.invoice_id.currency_id, account_invoice_line.quantity, account_invoice_line.product_id, account_invoice_line.invoice_id.partner_id)['taxes']
                for tax_line in tax_lines:
                    tax = self.env['account.tax'].browse(tax_line['id'])
                    if self.env.ref('l10n_in.cess_tag_tax').id in tax.tag_ids.ids:
                        cess_amount_count += tax_line.get('amount')
            record.cess_amount = cess_amount_count

    invoice_id = fields.Integer("Invoice Id")
    invoice_line_ids = fields.Char("invoice Line ids")
    invoice_date = fields.Char("Date")
    #product_hsn_code = fields.Char("HSN/SAC Code")
    #product_hsn_description = fields.Char("HSN/SAC Description")
    invoice_number = fields.Char("Invoice Number")
    #product_qty = fields.Float(string='Product Quantity')
    #uom_name = fields.Char(string='Reference Unit of Measure')
    #currency_code = fields.Char(string="Currency Code")
    partner_name = fields.Char(string="Parnter name")
    partner_pos = fields.Char(string="POS")
    partner_gstn = fields.Char(string="Parnter GSTN")
    #company_gstn = fields.Char(string='Company GSTN')
    price_total = fields.Float(string='Total Without Tax')
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
        ], string='Invoice Status', readonly=True)
    #country_code = fields.Char("Country Code")
    tax_rate = fields.Char("Rate")
    is_reverse_charge = fields.Boolean("Reverse Charge")
    port_code = fields.Char("Port Code")
    ecommerce_gstn = fields.Char("E-commerce GSTIN")
    is_ecommerce = fields.Char("Is E-commerce")
    b2b_invoice_type = fields.Selection([('R','Regular'),('DE','Deemed Exp'),
                                         ('SEWP','SEZ supplies with payment'),
                                         ('SEWOP','SEZ supplies without payment')], string="GST Invoice Type")
    exp_invoice_type = fields.Selection([('WPAY','WPAY'),
                                         ('WOPAY','WOPAY')], string="Export Type")
    refund_invoice_type = fields.Selection([('B2CL','B2CL'),
                                         ('EXPWP','EXPWP'),
                                         ('EXPWOP','EXPWP')], string="UR Type")
    refund_document_type = fields.Selection([('C', 'C'), ('D', 'D'), ('R', 'R')], string="Refund Document Type")
    refund_reason = fields.Char("Refund Reason")
    refund_invoice_number = fields.Char("Refund Invoice number")
    refund_invoice_date = fields.Char("Refund Invoice Date")
    invoice_total = fields.Float("Invoice Total")
    #company_id = fields.Integer("Company")
    #is_gst_tax = fields.Boolean("Is Gst Tax")
    tax_group_id = fields.Integer("Tax group")
    #is_down_payment = fields.Boolean("Is Down payment")
    cess_amount = fields.Float(compute="_get_cess_amount" ,string="Cess Amount", digits=0)

    _order = 'invoice_date desc'

    _depends = {
        'account.invoice': [
            'commercial_partner_id', 'company_id', 'e_commerce_partner_id',
            'currency_id', 'date_invoice', 'partner_id',
            'residual', 'state', 'type',
        ],
        'account.invoice.line': [
            'invoice_id', 'price_subtotal', 'product_id',
            'quantity', 'uom_id',
        ],
        'product.product': ['product_tmpl_id'],
        'res.partner': ['country_id', 'state_id'],
    }

    def _select(self):
        select_str = """
            SELECT row_number() OVER() AS id,
                min(sub.id) as invoice_id,
                array_agg(sub.invoice_line_id) as invoice_line_ids,
                sub.is_ecommerce as is_ecommerce,
                sub.ecommerce_gstn as ecommerce_gstn,
                sum(sub.price_total) as price_total,
                sub.tax_rate as tax_rate,
                sub.tax_group_id as tax_group_id,
                sub.type,
                sub.invoice_number,
                sub.is_reverse_charge,
                sub.b2b_invoice_type,
                sub.exp_invoice_type,
                sub.refund_invoice_type,
                sub.refund_document_type,
                sub.invoice_total,
                sub.partner_gstn,
                sub.partner_name,
                sub.invoice_date,
                sub.partner_pos,
                sub.port_code,
                sub.refund_reason,
                sub.refund_invoice_number,
                sub.refund_invoice_date,
                sub.state
        """
        return select_str

    def _sub_select(self):
        sub_select_str = """
                SELECT ail.invoice_id AS id,
                     ail.id AS invoice_line_id,
                     to_char(ai.date_invoice, 'DD-MON-YYYY') AS invoice_date,
                     (CASE WHEN ps.l10n_in_tin IS NOT NULL THEN concat(ps.l10n_in_tin,'-',ps.name) ELSE '' END) AS partner_pos,
                     p.vat AS partner_gstn,
                     p.name AS partner_name,
                     ai.type AS type,
                     ai.number AS invoice_number,
                     (CASE WHEN ai.is_reverse_charge THEN 'Y' ELSE 'N' END) AS is_reverse_charge,
                     (CASE WHEN ai.gst_invoice_type = ANY (ARRAY['DEWP', 'DEWOP']) THEN 'DE' ELSE ai.gst_invoice_type END) AS b2b_invoice_type,
                     (CASE WHEN ai.gst_invoice_type = ANY (ARRAY['DEWP', 'SEWP']) THEN 'WPAY' WHEN ai.gst_invoice_type = ANY (ARRAY['DEWOP', 'SEWOP']) THEN 'WOPAY' ELSE '' END) AS exp_invoice_type,
                     (CASE WHEN air.gst_invoice_type = ANY (ARRAY['DEWP', 'SEWP']) THEN 'EXPWP' WHEN air.gst_invoice_type = ANY (ARRAY['DEWOP', 'SEWOP']) THEN 'EXPWOP' ELSE 'B2CL' END) AS refund_invoice_type,
                     (CASE WHEN ai.type = 'in_refund' THEN 'D' WHEN ai.type = 'out_refund' THEN 'C' WHEN ai.type = 'out_refund' and aipr.payment_id != 0 then 'R' ELSE '' END) AS refund_document_type,
                     (CASE WHEN ai.type = ANY (ARRAY['in_refund', 'out_refund']) THEN ai.amount_total_company_signed * -1 ELSE ai.amount_total_company_signed END) AS invoice_total,
                     SUM(CASE WHEN ai.type = ANY (ARRAY['in_refund', 'out_refund']) THEN ail.price_subtotal_signed * -1 ELSE ail.price_subtotal_signed END) AS price_total,
                     ai.state AS state,
                     (CASE WHEN ecp.is_e_commerce THEN 'E' ELSE 'OE' END) AS is_ecommerce,
                     ecp.vat AS ecommerce_gstn,
                     dlmin.amount AS tax_rate,
                     gpc.code AS port_code,
                     (CASE WHEN airr.name IS NOT NULL THEN concat(airr.code,'-',airr.name) END) AS refund_reason,
                     air.number AS refund_invoice_number,
                     to_char(air.date_invoice, 'DD-MON-YYYY') AS refund_invoice_date,
                     max(dlmin.tax_group_id) AS tax_group_id
        """
        return sub_select_str

    def _from(self):
        from_str = """
            FROM account_invoice_line ail
                 JOIN account_invoice ai ON ai.id = ail.invoice_id
                 JOIN res_currency cr ON cr.id = ai.currency_id
                 JOIN res_company comp ON comp.id = ai.company_id
                 JOIN res_partner comp_pr ON comp_pr.id = comp.partner_id
                 JOIN res_partner p ON p.id = ai.commercial_partner_id
                 LEFT JOIN res_partner ecp ON ecp.id = ai.e_commerce_partner_id
                 LEFT JOIN res_country_state ps ON ps.id = p.state_id
                 LEFT JOIN gst_port_code gpc ON gpc.id = ai.port_code_id
                 LEFT JOIN product_product pr ON pr.id = ail.product_id
                 LEFT JOIN account_invoice_refund_reason airr ON airr.id = ai.refund_reason_id
                 LEFT JOIN account_invoice air on air.id = ai.refund_invoice_id
                 LEFT JOIN account_invoice_payment_rel aipr on aipr.invoice_id = ai.id
                 LEFT join (select min(atax.id) as id,
                    ailts.invoice_line_id as a_invoice_line_id,
                    CASE when atax.amount_type::text = 'group'
                        THEN sum(catax.amount)::character varying::text
                    ELSE sum(atax.amount)::character varying::text
                    END as amount,
                    CASE when atax.amount_type::text = 'group'
                        THEN max(catax.tax_group_id)
                    ELSE atax.tax_group_id
                    END as tax_group_id
                    from account_tax as atax
                    inner join account_invoice_line_tax as ailts ON (ailts.tax_id=atax.id)
                    LEFT JOIN account_tax_filiation_rel cataxr ON cataxr.parent_tax = atax.id
                    LEFT JOIN account_tax catax ON catax.id = cataxr.child_tax
                    group by a_invoice_line_id, atax.amount_type, atax.tax_group_id)
                    as dlmin on dlmin.a_invoice_line_id=ail.id
                where pr.id != %s

        """%(self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id',0))
        return from_str

    def _sub_group_by(self):
        sub_group_by_str = """
                GROUP BY ail.invoice_id,
                         ail.id,
                         ai.date_invoice,
                         ps.l10n_in_tin,
                         ps.name,
                         p.vat,
                         p.name,
                         ai.type,
                         ai.state,
                         ai.number,
                         ai.amount_total_company_signed,
                         ai.is_reverse_charge,
                         ai.gst_invoice_type,
                         aipr.payment_id,
                         air.number,
                         air.date_invoice,
                         dlmin.tax_group_id,
                         dlmin.amount,
                         ecp.is_e_commerce,
                         ecp.vat,
                         airr.name,
                         airr.code,
                         air.gst_invoice_type,
                         gpc.code
        """
        return sub_group_by_str

    def _group_by(self):
        group_by_str = """
        GROUP BY sub.id,
            sub.tax_rate,
            sub.is_ecommerce,
            sub.ecommerce_gstn,
            sub.type,
            sub.invoice_number,
            sub.b2b_invoice_type,
            sub.exp_invoice_type,
            sub.refund_invoice_type,
            sub.refund_document_type,
            sub.is_reverse_charge,
            sub.tax_group_id,
            sub.invoice_total,
            sub.partner_gstn,
            sub.partner_name,
            sub.invoice_date,
            sub.partner_pos,
            sub.port_code,
            sub.refund_reason,
            sub.refund_invoice_number,
            sub.refund_invoice_date,
            sub.state
        """
        return group_by_str




    @api.model_cr
    def init(self):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM (%s %s %s) as sub
            %s
        )""" % (self._table, self._select(), self._sub_select(), self._from(), self._sub_group_by() , self._group_by()))
