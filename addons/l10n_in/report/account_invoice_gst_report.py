# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo import tools
from odoo import models, fields, api
from odoo.addons.iap import jsonrpc
import json

DEFAULT_ENDPOINT = 'http://localhost:8070'

class AccountInvoiceGstReport(models.Model):
    _name = "account.invoice.gst.report"
    _description = "Invoices Statistics"
    _auto = False

    @api.multi
    def _get_cess_amount(self):
        for record in self:
            account_invoice_line = self.env['account.invoice.line'].browse([record.invoice_line_id])
            price_unit = account_invoice_line.price_unit * (1 - (account_invoice_line.discount or 0.0) / 100.0)
            tax_lines = account_invoice_line.invoice_line_tax_ids.compute_all(price_unit, account_invoice_line.invoice_id.currency_id, account_invoice_line.quantity, account_invoice_line.product_id, account_invoice_line.invoice_id.partner_id)['taxes']
            cess_amount_count = 0
            for tax_line in tax_lines:
                tax = self.env['account.tax'].browse(tax_line['id'])
                if self.env.ref('l10n_in.cess_tag_tax').id in tax.tag_ids.ids:
                    cess_amount_count += tax_line.get('amount')
            record.cess_amount = cess_amount_count

    invoice_line_id = fields.Integer("Invoice Line Id")
    date = fields.Date("Date")
    product_hsn_code = fields.Char("HSN/SAC Code")
    product_hsn_description = fields.Char("HSN/SAC Description")
    invoice_number = fields.Char("Invoice Number")
    product_qty = fields.Float(string='Product Quantity')
    uom_name = fields.Char(string='Reference Unit of Measure')
    currency_code = fields.Char(string="Currency Code")
    partner_name = fields.Char(string="Parnter name")
    partner_pos = fields.Char(string="POS")
    partner_gstn = fields.Char(string="Parnter GSTN")
    company_gstn = fields.Char(string='Company GSTN')
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
    country_code = fields.Char("Country Code")
    tax_rate = fields.Char("Rate")
    cess_amount = fields.Float(compute="_get_cess_amount" ,string="Cess Amount", digits=0)
    is_reverse_charge = fields.Boolean("Reverse Charge")
    port_code = fields.Char("Port Code")
    e_commerce_gstn = fields.Char("E-commerce GSTIN")
    is_e_commerce = fields.Boolean("Is E-commerce")
    gst_invoice_type = fields.Selection([('R', 'Regular'), ('DE', 'Deemed Exports'),
                                         ('SEWP', 'SEZ Exports with payment'),
                                         ('SEWOP', 'SEZ exports without payment')], string="GST Invoice Type")
    refund_reason = fields.Char("Refund Reason")
    refund_invoice_number = fields.Char("Refund Invoice number")
    refund_invoice_data = fields.Char("Refund Invoice_number")
    invoice_total = fields.Float("Invoice Total")
    company_id = fields.Integer("Company")


    _order = 'date desc'

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
                    ail.id AS invoice_line_id,
                    ai.date_invoice AS date,
                    pt.l10n_in_hsn_code AS product_hsn_code,
                    pt.l10n_in_hsn_description AS product_hsn_description,
                    u2.name AS uom_name,
                    cr.name AS currency_code,
                    comp_pr.vat AS company_gstn,
                    ai.company_id AS company_id,
                    ai.type AS type,
                    ai.state AS state,
                    air.number AS refund_invoice_number,
                    air.date_invoice AS refund_invoice_data,
                    SUM((ail.quantity) / u.factor * u2.factor) AS product_qty,
                    SUM(ail.price_subtotal) AS price_total,
                    ai.amount_total AS invoice_total,
                    p.name AS partner_name,
                    p.vat AS partner_gstn,
                    ps.code AS partner_pos,
                    ailt.rate AS tax_rate,
                    ai.number AS invoice_number,
                    ai.is_reverse_charge AS is_reverse_charge,
                    ai.gst_invoice_type AS gst_invoice_type,
                    gpc.code AS port_code,
                    ecp.vat AS e_commerce_gstn,
                    ecp.is_e_commerce AS is_e_commerce,
                    airr.name AS refund_reason,
                    pc.code AS country_code
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_invoice_line ail
                JOIN account_invoice ai ON ai.id = ail.invoice_id
                JOIN res_currency cr ON cr.id = ai.currency_id
                JOIN res_company comp ON comp.id = ai.company_id
                JOIN res_partner comp_pr ON comp_pr.id = comp.partner_id
                JOIN res_partner p ON p.id = ai.commercial_partner_id
                LEFT JOIN res_country_state ps ON ps.id = p.state_id
                LEFT JOIN res_country pc ON pc.id = p.country_id
                LEFT JOIN res_partner ecp ON ecp.id = ai.e_commerce_partner_id
                LEFT JOIN account_invoice_refund_reason airr ON airr.id = ai.refund_reason_id
                LEFT JOIN gst_port_code gpc ON gpc.id = ai.port_code_id
                LEFT JOIN account_invoice_line_tax ailts ON ailts.invoice_line_id = ail.id
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                LEFT JOIN product_template pt ON pt.id = pr.product_tmpl_id
                LEFT JOIN product_uom u ON u.id = ail.uom_id
                LEFT JOIN product_uom u2 ON u2.id = pt.uom_id
                LEFT JOIN account_invoice air on air.id = ai.refund_invoice_id
                LEFT JOIN (

                    --Temporary table to decide gst rate
                    select at.id,(
                    CASE when at.tax_group_id = ANY (ARRAY%s)
                        THEN CASE when at.amount_type::text = 'group'
                            THEN sum(ctx.amount)::character varying::text
                            ELSE sum(at.amount)::character varying::text
                            END
                        ELSE at.name::character varying::text
                    END) as rate  from account_tax at
                    LEFT JOIN account_tax_filiation_rel ctxr ON ctxr.parent_tax = at.id
                    LEFT JOIN account_tax ctx ON ctx.id = ctxr.child_tax
                    group by at.id, at.name

                ) ailt ON ailt.id = ailts.tax_id
                where ai.state = ANY (ARRAY['open','paid','cancel']) and comp.register_gst_service = True
        """%(self.get_all_gst_groups())
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ail.id,
                        ai.date_invoice,
                        ai.company_id,
                        pt.l10n_in_hsn_code,
                        pt.l10n_in_hsn_description,
                        u2.name,
                        cr.name,
                        comp_pr.vat,
                        ai.type,
                        ai.state,
                        air.number,
                        air.date_invoice,
                        p.name,
                        p.vat,
                        ps.code,
                        ailt.rate,
                        ai.number,
                        ai.is_reverse_charge,
                        ai.gst_invoice_type,
                        ai.amount_total,
                        ecp.vat,
                        ecp.is_e_commerce,
                        gpc.code,
                        airr.name,
                        pc.code
        """
        return group_by_str

    @api.model_cr
    def init(self):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            %s
            %s
        )""" % (
                    self._table, self._select(), self._from(), self._group_by()))


    def get_all_gst_groups(self):
        gst_group = self.env.ref('l10n_in.gst_group', False)
        igst_group = self.env.ref('l10n_in.igst_group', False)
        return [gst_group and gst_group.id or False, igst_group and igst_group.id or False]

    @api.model
    def send_gstr_data_to_server(self, company_id = False ,inv_domain = [], payment_domain = []):
        ir_params = self.env['ir.config_parameter'].sudo()
        user_token = self.env['iap.account'].get('gst_retrun_sandbox')
        for company in self.env['res.company'].search([('register_gst_service','=',True)]):
            params = {
                'account_token': user_token.account_token,
                'company_gstn':company.vat,
                'dbuuid':ir_params.sudo().get_param('database.uuid'),
                'invoice_datas':self.sudo().search_read([('company_id','=',company.id)] + inv_domain),
                'payment_datas':self.env['account.payment.report'].sudo().search_read([('company_id','=',company.id)] + payment_domain),
                'force_update': payment_domain or inv_domain if  True else False,
            }
            # ir.config_parameter allows locally overriding the endpoint
            # for testing & al
            endpoint = ir_params.get_param('gst_retrun_sandbox.endpoint', DEFAULT_ENDPOINT)
            jsonrpc(endpoint + '/gstr_retrun/upload', params=params)
