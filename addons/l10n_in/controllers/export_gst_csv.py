# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import mimetypes
import os
import re
import io
import calendar
import datetime
import json
import uuid

from odoo.http import request

from odoo.tools.misc import str2bool, xlwt, file_open

from odoo import fields, http, _
from odoo.addons.web.controllers.main import content_disposition
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.web.controllers.main import CSVExport


class ExportGstCsv(CSVExport):

    @http.route(['/csv/download/<model("export.gst.return.csv"):gst_retrun>'], type='http', auth='public')
    def download_xls_report(self, gst_retrun, **post):
        return self.base(json.dumps(self.get_type_wise_date(gst_retrun.export_summary, gst_retrun.month, gst_retrun.year)), uuid.uuid4().hex)

    def get_type_wise_date(self, type, month, year):
        csv_fields = csv_domain = []
        csv_model = ""
        if type == 'b2b':
            csv_model = 'account.invoice.gst.report'
            csv_domain = [['type', '=', 'out_invoice'],['tax_group_id', 'in', self.get_all_gst_groups()],['partner_gstn','!=', False]]
            csv_fields = [{"name": "partner_gstn", "label": "GSTIN/UIN of Recipient"},
                         {"name": "partner_name", "label": "Receiver Name"},
                         {"name": "invoice_number", "label": "Invoice Number"},
                         {"name": "invoice_date", "label": "Invoice date"},
                         {"name": "invoice_total", "label": "Invoice Value"},
                         {"name": "partner_pos", "label": "Place Of Supply"},
                         {"name": "is_reverse_charge", "label": "Reverse Charge"},
                         {"name": "b2b_invoice_type", "label": "Invoice Type"},
                         {"name": "ecommerce_gstn", "label": "E-Commerce GSTIN"},
                         {"name": "tax_rate", "label": "Rate"},
                         {"name": "price_total", "label": "Taxable Value"},
                         {"name": "cess_amount", "label": "Cess Amount"}
                        ]
        if type == 'b2cl':
            csv_model = 'account.invoice.gst.report'
            csv_domain = [['type', '=', 'out_invoice'],['tax_group_id', 'in', self.get_all_gst_groups()],['partner_gstn','=', False]]
            csv_fields = [{"name": "invoice_number", "label": "Invoice Number"},
                         {"name": "invoice_date", "label": "Invoice date"},
                         {"name": "invoice_total", "label": "Invoice Value"},
                         {"name": "partner_pos", "label": "Place Of Supply"},
                         {"name": "tax_rate", "label": "Rate"},
                         {"name": "price_total", "label": "Taxable Value"},
                         {"name": "cess_amount", "label": "Cess Amount"},
                         {"name": "ecommerce_gstn", "label": "E-Commerce GSTIN"}
                        ]
        if type == 'b2cs':
            csv_model = 'account.invoice.gst.report'
            csv_domain = [['type', '=', 'out_invoice'],['tax_group_id', 'in', self.get_all_gst_groups()],['partner_gstn','=', False]]
            csv_fields = [{"name": "is_ecommerce", "label": "Type"},
                         {"name": "partner_pos", "label": "Place Of Supply"},
                         {"name": "tax_rate", "label": "Rate"},
                         {"name": "price_total", "label": "Taxable Value"},
                         {"name": "cess_amount", "label": "Cess Amount"},
                         {"name": "ecommerce_gstn", "label": "E-Commerce GSTIN"}
                        ]
        if type == 'cdnr':
            csv_model = 'account.invoice.gst.report'
            csv_domain = [['type', 'in', ['out_refund','in_refund']],['tax_group_id', 'in', self.get_all_gst_groups()],['partner_gstn','!=', False]]
            csv_fields = [{"name": "partner_gstn", "label": "GSTIN/UIN of Recipient"},
                          {"name": "partner_name", "label": "Receiver Name"},
                          {"name": "refund_invoice_number", "label": "Invoice/Advance Receipt Number"},
                          {"name": "refund_invoice_date", "label": "Invoice/Advance Receipt date"},
                          {"name": "invoice_number", "label": "Note/Refund Voucher Number"},
                          {"name": "invoice_date", "label": "Note/Refund Voucher date"},
                          {"name": "refund_document_type", "label": "Document Type"},
                          {"name": "refund_reason", "label": "Reason For Issuing document"},
                          {"name": "partner_pos", "label": "Place Of Supply"},
                          {"name": "invoice_total", "label": "Note/Refund Voucher Value"},
                          {"name": "tax_rate", "label": "Rate"},
                          {"name": "price_total", "label": "Taxable Value"},
                          {"name": "cess_amount", "label": "Cess Amount"},
                          #{"name": "", "label": "Pre GST"}
                          ]
        if type == 'cdnur':
            csv_model = 'account.invoice.gst.report'
            csv_domain = [['type', 'in', ['out_refund','in_refund']],['tax_group_id', 'in', self.get_all_gst_groups()],['partner_gstn','=', False]]
            csv_fields = [
                        {"name": "refund_invoice_type", "label": "UR Type"},
                        {"name": "invoice_number", "label": "Note/Refund Voucher Number"},
                        {"name": "invoice_data", "label": "Note/Refund Voucher date"},
                        {"name": "refund_document_type", "label": "Document Type"},
                        {"name": "refund_invoice_number", "label": "Invoice/Advance Receipt Number"},
                        {"name": "refund_invoice_data", "label": "Invoice/Advance Receipt date"},
                        {"name": "refund_reason", "label": "Reason For Issuing document"},
                        {"name": "partner_pos", "label": "Place Of Supply"},
                        {"name": "invoice_total", "label": "Note/Refund Voucher Value"},
                        {"name": "tax_rate", "label": "Rate"},
                        {"name": "price_total", "label": "Taxable Value"},
                        {"name": "cess_amount", "label": "Cess Amount"},
                        #{"name": "", "label": "Pre GST"}
                        ]
        if type == 'exp':
            csv_model = 'account.invoice.gst.report'
            csv_domain = [['type', '=', 'out_invoice'],['tax_group_id', 'in', self.get_all_gst_groups()],['exp_invoice_type','in',['WPAY','WOPAY']]]
            csv_fields = [
                        {"name": "exp_invoice_type", "label": "Export Type"},
                        {"name": "invoice_number", "label": "Invoice Number"},
                        {"name": "invoice_date", "label": "Invoice date"},
                        {"name": "invoice_total", "label": "Invoice Value"},
                        {"name": "port_code", "label": "Port Code"},
                        #{"name": "", "label": "Shipping Bill Number"},
                        #{"name": "", "label": "Shipping Bill Date"},
                        {"name": "tax_rate", "label": "Rate"},
                        {"name": "price_total", "label": "Taxable Value"}
                        ]
        if type == 'at':
            csv_model = 'account.payment.report'
            csv_domain = [['amount', '>', 0], ['internal_type', '=', 'receivable']]
            csv_fields = [{"name": "state_code", "label": "Place Of Supply"},
                         {"name": "tax_rate", "label": "Rate"},
                         {"name": "amount", "label": "Gross Advance Received"},
                         #{"name": "", "label": "Cess Amount"}
                        ]
        return {'fields': csv_fields,
                'import_compat': False,
                'domain': csv_domain,
                'model': csv_model,'ids': []}

    def get_all_gst_groups(self):
        gst_group = request.env.ref('l10n_in.gst_group', False)
        igst_group = request.env.ref('l10n_in.igst_group', False)
        return [gst_group and gst_group.id or 0, igst_group and igst_group.id or 0]
