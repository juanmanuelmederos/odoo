# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tools import pycompat
from .test_sale_common import TestCommonSaleNoChart


class TestSaleToInvoice(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleToInvoice, cls).setUpClass()
        cls.setUpClassicProducts()
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

        # Create the sale order with four order lines
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_customer_usd.id,
            'order_line': [
                (0, 0, {'product_id': cls.product_order.id, 'product_uom_qty': 5.0}),
                (0, 0, {'product_id': cls.service_deliver.id, 'product_uom_qty': 4.0}),
                (0, 0, {'product_id': cls.service_order.id, 'product_uom_qty': 3.0}),
                (0, 0, {'product_id': cls.product_deliver.id, 'product_uom_qty': 2.0}),
            ]
        })

        # Context
        cls.context = {
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.journal_sale
        }

    def test_downpayment(self):
        """ Test invoice with downpayment """
        # Confirm the SO
        self.sale_order.action_confirm()
        # Let's do an invoice for a deposit of 100
        payment_form = Form(self.env['sale.advance.payment.inv'].with_context(self.context))
        payment_form.advance_payment_method = 'fixed'
        payment_form.amount = 100
        payment_form.deposit_account_id = self.account_income
        payment = payment_form.save()
        payment.create_invoices()

        # Check that an invoice created or not
        assert self.sale_order.invoice_ids, "An invoice should be created for this sales order"
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEquals(len(downpayment_line), 1, 'SO line downpayment should be created on SO')

        with Form(self.sale_order) as order:
            with order.order_line.edit(1) as line:
                line.qty_delivered = 4
            with order.order_line.edit(3) as line:
                line.qty_delivered = 2

        # Let's do an invoice with refunds
        payment_form = Form(self.env['sale.advance.payment.inv'].with_context(self.context))
        payment_form.advance_payment_method = 'all'
        payment_form.deposit_account_id = self.account_income
        payment = payment_form.save()
        payment.create_invoices()

        assert self.sale_order.invoice_ids, "An invoice should be created for this sales order"

        invoice = self.sale_order.invoice_ids[0]
        self.assertEquals(len(invoice.invoice_line_ids), len(self.sale_order.order_line), 'All lines should be invoiced')
        self.assertEquals(invoice.amount_total, self.sale_order.amount_total - downpayment_line.price_unit, 'Downpayment should be applied')

    def test_invoice_with_discount(self):
        """ Test invoice with discount """
        with Form(self.sale_order) as order:
            with order.order_line.edit(0) as line:
                line.discount = 20
            with order.order_line.edit(1) as line:
                line.discount = 20
                line.qty_delivered = 4
            with order.order_line.edit(2) as line:
                line.discount = -10
            with order.order_line.edit(3) as line:
                line.qty_delivered = 2

        for line in self.sale_order.order_line.filtered(lambda l: l.discount):
            product_price = line.price_unit * line.product_uom_qty
            self.assertEquals(line.discount, (product_price - line.price_subtotal)/product_price*100, 'Discount should be applied on order line')

        self.sale_order.action_confirm()
        # Let's do an invoice with invoiceable lines
        payment_form = Form(self.env['sale.advance.payment.inv'].with_context(self.context))
        payment_form.advance_payment_method = 'delivered'
        payment = payment_form.save()
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]
        invoice.action_invoice_open()

        for line, inv_line in pycompat.izip(self.sale_order.order_line, invoice.invoice_line_ids):
            self.assertEquals(line.discount, inv_line.discount, 'Discount on lines of order and invoice should be same')

    def test_invoice_refund(self):
        """ Test invoice with refund """
        self.sale_order.action_confirm()
        # Take only invoicable line
        order_line = self.sale_order.order_line.filtered(lambda l: l.product_id.invoice_policy == 'order')

        for line in order_line:
            self.assertEquals(line.qty_to_invoice, line.product_uom_qty, 'Quantity to invoice should be same as ordered quantity')
            self.assertEquals(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')

        # Let's do an invoice with invoiceable lines
        payment_form = Form(self.env['sale.advance.payment.inv'].with_context(self.context))
        payment_form.advance_payment_method = 'delivered'
        payment = payment_form.save()
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        with Form(invoice) as inv:
            with inv.invoice_line_ids.edit(0) as line:
                line.quantity = 3
            with inv.invoice_line_ids.edit(1) as line:
                line.quantity = 2

        invoice.action_invoice_open()
        for line in order_line:
            self.assertEquals(line.qty_to_invoice, line.product_uom_qty - line.qty_invoiced, 'Quantity to invoice should be a difference between ordered quantity and invoiced quantity')

        # Make a credit note
        credit_note_form = Form(self.env['account.invoice.refund'].with_context({'active_ids': [invoice.id], 'active_id': invoice.id}))
        credit_note_form.filter_refund = 'refund'
        credit_note_form.description = 'test'
        credit_note = credit_note_form.save()
        credit_note.invoice_refund()

        invoice_1 = self.sale_order.invoice_ids[0]
        invoice_1.action_invoice_open()
