# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    refund_reason_id = fields.Many2one("account.invoice.refund.reason", string="Selected Reason")
    port_code_id = fields.Many2one("gst.port.code", string="Port Code")
    is_reverse_charge = fields.Boolean("Reverse Charge", help="Tick This if invoice is reverse charge")

    def _get_printed_report_name(self):
        self.ensure_one()
        if self.company_id.country_id.code != 'IN':
            return super(AccountInvoice, self)._get_printed_report_name()
        return self.type == 'out_invoice' and self.state == 'draft' and _('Draft %s') % (self.journal_id.name) or \
            self.type == 'out_invoice' and self.state in ('open','paid') and '%s - %s' % (self.journal_id.name, self.number) or \
            self.type == 'out_refund' and self.state == 'draft' and _('Credit Note') or \
            self.type == 'out_refund' and _('Credit Note - %s') % (self.number) or \
            self.type == 'in_invoice' and self.state == 'draft' and _('Vendor Bill') or \
            self.type == 'in_invoice' and self.state in ('open','paid') and _('Vendor Bill - %s') % (self.number) or \
            self.type == 'in_refund' and self.state == 'draft' and _('Vendor Credit Note') or \
            self.type == 'in_refund' and _('Vendor Credit Note - %s') % (self.number)

    @api.multi
    def _invoice_line_tax_values(self):
        self.ensure_one()
        tax_datas = {}
        TAX = self.env['account.tax']

        for line in self.mapped('invoice_line_ids'):
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.invoice_line_tax_ids.compute_all(price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id)['taxes']
            for tax_line in tax_lines:
                tax_line['tag_ids'] = TAX.browse(tax_line['id']).tag_ids.ids
            tax_datas[line.id] = tax_lines
        return tax_datas

    @api.model
    def _get_gst_tag_ids(self):
        return {
                'cgst_tag_tax_id': self.env.ref('l10n_in.cgst_tag_tax').id,
                'sgst_tag_tax_id': self.env.ref('l10n_in.sgst_tag_tax').id,
                'igst_tag_tax_id': self.env.ref('l10n_in.igst_tag_tax').id,
                'cess_tag_tax_id': self.env.ref('l10n_in.cess_tag_tax').id,
                }

    @api.multi
    def _get_group_by_hsn_data(self):
        self.ensure_one()
        tax_datas = {}
        TAX = self.env['account.tax']
        company_id = self.env.user.company_id
        gst_tag = self._get_gst_tag_ids()
        hsn_group_data = {}
        for line in self.mapped('invoice_line_ids'):
            igst_amount = cgst_amount = sgst_amount = cess_amount = 0
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.invoice_line_tax_ids.compute_all(price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id)['taxes']
            for tax_line in tax_lines:
                tax = TAX.browse(tax_line['id'])
                tax_rate = tax.amount
                tag_ids = tax.tag_ids.ids

                igst_amount += tax_line.get('amount') if gst_tag.get('cgst_tag_tax_id') in tag_ids else 0
                cgst_amount += tax_line.get('amount') if gst_tag.get('cgst_tag_tax_id') in tag_ids else 0
                sgst_amount += tax_line.get('amount') if gst_tag.get('cgst_tag_tax_id') in tag_ids else 0
                cess_amount += tax_line.get('amount') if gst_tag.get('cgst_tag_tax_id') in tag_ids else 0
                if invoice.currency_id != request.env.user.company_id.currency_id:
                    igst_amount = invoice.currency_id.with_context(date=invoice.date_invoice).compute(igst_amount, company_id.currency_id)
                    cgst_amount = invoice.currency_id.with_context(date=invoice.date_invoice).compute(cgst_amount, company_id.currency_id)
                    sgst_amount = invoice.currency_id.with_context(date=invoice.date_invoice).compute(sgst_amount, company_id.currency_id)
                    cess_amount = invoice.currency_id.with_context(date=invoice.date_invoice).compute(cess_amount, company_id.currency_id)

                hsn_group_key = (line.product_id.l10n_in_hsn_code , line.product_id.l10n_in_hsn_description, line.uom_id.name or '')
                hsn_group_data.setdefault(hsn_group_key, {}).update({
                    'hsn_code':line.product_id.l10n_in_hsn_code,
                    'hsn_description':line.product_id.l10n_in_hsn_description,
                    'uom': line.uom_id.name,
                    'quantity': line.quantity + hsn_group_data[hsn_group_key].get('quantity', 0),
                    'price_total': line.price_total + hsn_group_data[hsn_group_key].get('price_total', 0),
                    'taxable_value': line.price_subtotal_signed + hsn_group_data[hsn_group_key].get('taxable_value', 0),
                    'igst': igst_amount + hsn_group_data[hsn_group_key].get('igst', 0),
                    'cgst': cgst_amount + hsn_group_data[hsn_group_key].get('cgst', 0),
                    'sgst': sgst_amount + hsn_group_data[hsn_group_key].get('sgst', 0),
                    'cess': cess_amount + hsn_group_data[hsn_group_key].get('cess', 0),
                    })
        return hsn_group_data

    @api.multi
    def _invoice_line_group_tax_values(self):
        self.ensure_one()
        tax_datas = {}
        TAX = self.env['account.tax']
        company_id = self.env.user.company_id
        gst_tag = self._get_gst_tag_ids()
        for line in self.mapped('invoice_line_ids'):
            rate = base_amount = cess_amount = 0
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            tax_lines = line.invoice_line_tax_ids.compute_all(price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id)['taxes']
            for tax_line in tax_lines:
                tax = TAX.browse(tax_line['id'])
                tax_rate = tax.amount
                tag_ids = tax.tag_ids.ids
                base_amount = tax_line.get('base')
                if gst_tag['cgst_tag_tax_id'] in tag_ids:
                    rate += tax_rate
                if gst_tag['sgst_tag_tax_id'] in tag_ids:
                    rate += tax_rate
                if gst_tag['igst_tag_tax_id'] in tag_ids:
                    rate = tax_rate
                if gst_tag['cess_tag_tax_id'] in tag_ids:
                    cess_amount += tax_line.get('amount')
            base_amount = self.currency_id.with_context(date=self.date_invoice).compute(base_amount, company_id.currency_id)
            tax_datas.setdefault(rate, {}).update({'base_amount': base_amount + (tax_datas[rate].get('base_amount', 0)), 'cess_amount': cess_amount + (tax_datas[rate].get('cess_amount', 0))})
        return tax_datas
