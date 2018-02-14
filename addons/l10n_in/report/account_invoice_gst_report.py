# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo import tools
from odoo import models, fields, api
from odoo.addons.iap import jsonrpc

DEFAULT_ENDPOINT = 'http://localhost:8070'

class AccountInvoiceGstReport(models.Model):
    _name = "account.invoice.gst.report"
    _description = "Invoices Statistics"
    _auto = False

    @api.multi
    def _get_cess_amount(self):
        for record in self:
            account_invoice_line = self.env['account.invoice.line'].browse([record.ail_id])
            price_unit = account_invoice_line.price_unit * (1 - (account_invoice_line.discount or 0.0) / 100.0)
            tax_lines = account_invoice_line.invoice_line_tax_ids.compute_all(price_unit, account_invoice_line.invoice_id.currency_id, account_invoice_line.quantity, account_invoice_line.product_id, account_invoice_line.invoice_id.partner_id)['taxes']
            cess_amount_count = 0
            for tax_line in tax_lines:
                tax = self.env['account.tax'].browse(tax_line['id'])
                if self.env.ref('l10n_in.cess_tag_tax').id in tax.tag_ids.ids:
                    cess_amount_count += tax_line.get('amount')
            record.cess_amount = cess_amount_count

    ail_id = fields.Integer("Invoice Line Id")
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
    gst_invoice_type = fields.Char("Gst Invoice Type")
    refund_reason = fields.Char("Refund Reason")


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
                    ail.id AS ail_id,
                    ai.date_invoice AS date,
                    pt.l10n_in_hsn_code AS product_hsn_code,
                    pt.l10n_in_hsn_description AS product_hsn_description,
                    u2.name AS uom_name,
                    cr.name AS currency_code,
                    comp_pr.vat AS company_gstn,
                    ai.type AS type,
                    ai.state AS state,
                    SUM ((invoice_type.sign * ail.quantity) / u.factor * u2.factor) AS product_qty,
                    SUM(ail.price_subtotal_signed * invoice_type.sign) AS price_total,
                    partner.name AS partner_name,
                    partner_state.code AS partner_pos,
                    partner.vat AS partner_gstn,
                    taxs_rate.rate AS tax_rate,
                    ai.number AS invoice_number,
                    ai.is_reverse_charge AS is_reverse_charge,
                    ai.gst_invoice_type AS gst_invoice_type,
                    pc.code AS port_code,
                    e_partner.vat AS e_commerce_gstn,
                    e_partner.is_e_commerce AS is_e_commerce,
                    airr.name AS refund_reason,
                    partner_country.code AS country_code
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_invoice_line ail
                JOIN account_invoice ai ON ai.id = ail.invoice_id
                JOIN res_currency cr ON cr.id = ai.currency_id
                JOIN res_company comp ON comp.id = ai.company_id
                JOIN res_partner comp_pr ON comp_pr.id = comp.partner_id
                JOIN res_partner partner ON partner.id = ai.commercial_partner_id
                LEFT JOIN res_country_state partner_state ON partner_state.id = partner.state_id
                LEFT JOIN res_country partner_country ON partner_country.id = partner.country_id
                LEFT JOIN res_partner e_partner ON e_partner.id = ai.e_commerce_partner_id
                LEFT JOIN account_invoice_refund_reason airr ON airr.id = ai.refund_reason_id
                LEFT JOIN gst_port_code pc ON pc.id = ai.port_code_id
                LEFT JOIN account_invoice_line_tax invoice_line_tax ON invoice_line_tax.invoice_line_id = ail.id
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                LEFT JOIN product_template pt ON pt.id = pr.product_tmpl_id
                LEFT JOIN product_uom u ON u.id = ail.uom_id
                LEFT JOIN product_uom u2 ON u2.id = pt.uom_id
                JOIN (
                    -- Temporary table to decide if the qty should be added or retrieved (Invoice vs Credit Note)
                    SELECT id,(CASE
                         WHEN ai.type::text = ANY (ARRAY['in_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN -1
                            ELSE 1
                        END) AS sign
                    FROM account_invoice ai
                ) AS invoice_type ON invoice_type.id = ai.id
                LEFT JOIN (

                    --Temporary table to decide gst rate
                    select account_tax.id,(
                    CASE when account_tax.name::text ilike ANY (ARRAY['%GST%'::character varying::text,'%IGST%'::character varying::text])
                        THEN CASE when account_tax.amount_type::text = 'group'
                            THEN sum(child_tax_tax.amount)::character varying::text
                            ELSE sum(account_tax.amount)::character varying::text
                            END
                        ELSE account_tax.name::character varying::text
                    END) as rate  from account_tax
                    LEFT JOIN account_tax_filiation_rel child_tax ON account_tax.id = child_tax.parent_tax
                    LEFT JOIN account_tax child_tax_tax ON  child_tax = child_tax_tax.id
                    group by account_tax.id, account_tax.name

                ) taxs_rate ON invoice_line_tax.tax_id = taxs_rate.id
                where ai.state = ANY (ARRAY['open','paid','cancel']) and comp.register_gst_service = True
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ail.id,
                        ai.date_invoice,
                        pt.l10n_in_hsn_code,
                        pt.l10n_in_hsn_description,
                        u2.name,
                        cr.name,
                        comp_pr.vat,
                        ai.type,
                        ai.state,
                        partner.name,
                        partner_state.code,
                        partner.vat,
                        taxs_rate.rate,
                        ai.number,
                        ai.is_reverse_charge,
                        ai.gst_invoice_type,
                        e_partner.vat,
                        e_partner.is_e_commerce,
                        pc.code,
                        airr.name,
                        partner_country.code
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



    @api.model
    def send_gstr_data_to_server(self, inv_domain = [], payment_domain = []):
        ir_params = self.env['ir.config_parameter'].sudo()
        user_token = self.env['iap.account'].get('gst_retrun_sandbox')
        params = {
            'account_token': user_token.account_token,
            'dbuuid':ir_params.sudo().get_param('database.uuid'),
            'invoice_data':self.sudo().search_read(inv_domain),
            'payment_data':self.env['account.payment.report'].sudo().search_read(payment_domain),
            'force_update': payment_domain or inv_domain if  True else False,
        }
        # ir.config_parameter allows locally overriding the endpoint
        # for testing & al
        endpoint = ir_params.get_param('gst_retrun_sandbox.endpoint', DEFAULT_ENDPOINT)
        jsonrpc(endpoint + '/gstr_retrun/upload_data', params=params)
