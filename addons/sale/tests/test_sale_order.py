# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form
from odoo.tools import float_compare

from .test_sale_common import TestCommonSaleNoChart


class TestSaleOrder(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleOrder, cls).setUpClass()

        cls.Pricelist = cls.env['product.pricelist']
        cls.PricelistItem = cls.env['product.pricelist.item']
        cls.SaleOrderLine = cls.env['sale.order.line']
        # set up users
        cls.setUpUsers()
        group_salemanager = cls.env.ref('sales_team.group_sale_manager')
        group_salesman = cls.env.ref('sales_team.group_sale_salesman')
        cls.user_manager.write({'groups_id': [(6, 0, [group_salemanager.id])]})
        cls.user_employee.write({'groups_id': [(6, 0, [group_salesman.id])]})

        # set up accounts and products and journals
        cls.setUpAdditionalAccounts()
        cls.setUpClassicProducts()
        cls.setUpAccountJournal()

        # Create a pricelist with/without discount policy
        cls.pricelist_with_disct = cls.Pricelist.create({
            'name': 'Pricelist A',
            'discount_policy': 'with_discount',
        })
        cls.pricelist_without_disct = cls.Pricelist.create({
            'name': 'Pricelist B',
            'discount_policy': 'without_discount',
        })

        # Create the SO with pricelist
        cls.sale_order_pricelist = cls.env['sale.order'].create({
            'partner_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_with_disct.id
        })

        # create a generic Sale Order with all classical products
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_customer_usd.id,
            'partner_invoice_id': cls.partner_customer_usd.id,
            'partner_shipping_id': cls.partner_customer_usd.id,
            'pricelist_id': cls.pricelist_usd.id,
        })
        cls.sol_product_order = cls.env['sale.order.line'].create({
            'name': cls.product_order.name,
            'product_id': cls.product_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_order.uom_id.id,
            'price_unit': cls.product_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = cls.env['sale.order.line'].create({
            'name': cls.service_deliver.name,
            'product_id': cls.service_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_deliver.uom_id.id,
            'price_unit': cls.service_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = cls.env['sale.order.line'].create({
            'name': cls.service_order.name,
            'product_id': cls.service_order.id,
            'product_uom_qty': 2,
            'product_uom': cls.service_order.uom_id.id,
            'price_unit': cls.service_order.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_prod_deliver = cls.env['sale.order.line'].create({
            'name': cls.product_deliver.name,
            'product_id': cls.product_deliver.id,
            'product_uom_qty': 2,
            'product_uom': cls.product_deliver.uom_id.id,
            'price_unit': cls.product_deliver.list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_order(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        # DBO TODO: validate invoice and register payments
        Invoice = self.env['account.invoice']
        self.sale_order.order_line.read(['name', 'price_unit', 'product_uom_qty', 'price_total'])

        self.assertEqual(self.sale_order.amount_total, sum([2 * p.list_price for p in self.product_map.values()]), 'Sale: total amount is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)
        # send quotation
        self.sale_order.force_quotation_send()
        self.assertTrue(self.sale_order.state == 'sent', 'Sale: state after sending is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)

        # confirm quotation
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.invoice_status == 'to invoice')

        # create invoice: only 'invoice on order' products are invoiced
        inv_id = self.sale_order.action_invoice_create()
        invoice = Invoice.browse(inv_id)
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'Sale: invoice is missing lines')
        self.assertEqual(invoice.amount_total, sum([2 * p.list_price if p.invoice_policy == 'order' else 0 for p in self.product_map.values()]), 'Sale: invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 1, 'Sale: invoice is missing')
        self.sale_order.order_line._compute_product_updatable()
        self.assertFalse(self.sale_order.order_line[0].product_updatable)

        # deliver lines except 'time and material' then invoice again
        for line in self.sale_order.order_line:
            line.qty_delivered = 2 if line.product_id.expense_policy == 'no' else 0
        self.assertTrue(self.sale_order.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        inv_id = self.sale_order.action_invoice_create()
        invoice2 = Invoice.browse(inv_id)
        self.assertEqual(len(invoice2.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(invoice2.amount_total, sum([2 * p.list_price if p.invoice_policy == 'delivery' else 0 for p in self.product_map.values()]), 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything should be "invoiced"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 2, 'Sale: invoice is missing')

        # go over the sold quantity
        self.sol_serv_order.write({'qty_delivered': 10})
        self.assertTrue(self.sale_order.invoice_status == 'upselling', 'Sale: SO status after increasing delivered qty higher than ordered qty should be "upselling"')

        # upsell and invoice
        self.sol_serv_order.write({'product_uom_qty': 10})

        inv_id = self.sale_order.action_invoice_create()
        invoice3 = Invoice.browse(inv_id)
        self.assertEqual(len(invoice3.invoice_line_ids), 1, 'Sale: third invoice is missing lines')
        self.assertEqual(invoice3.amount_total, 8 * self.product_map['serv_order'].list_price, 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_unlink_cancel(self):
        """ Test deleting and cancelling sales orders depending on their state and on the user's rights """
        # SO in state 'draft' can be deleted
        so_copy = self.sale_order.copy()
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user_employee).unlink()
        self.assertTrue(so_copy.sudo(self.user_manager).unlink(), 'Sale: deleting a quotation should be possible')

        # SO in state 'cancel' can be deleted
        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == 'sale', 'Sale: SO should be in state "sale"')
        so_copy.action_cancel()
        self.assertTrue(so_copy.state == 'cancel', 'Sale: SO should be in state "cancel"')
        with self.assertRaises(AccessError):
            so_copy.sudo(self.user_employee).unlink()
        self.assertTrue(so_copy.sudo(self.user_manager).unlink(), 'Sale: deleting a cancelled SO should be possible')

        # SO in state 'sale' or 'done' cannot be deleted
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale', 'Sale: SO should be in state "sale"')
        with self.assertRaises(UserError):
            self.sale_order.sudo(self.user_manager).unlink()

        self.sale_order.action_done()
        self.assertTrue(self.sale_order.state == 'done', 'Sale: SO should be in state "done"')
        with self.assertRaises(UserError):
            self.sale_order.sudo(self.user_manager).unlink()

    def test_cost_invoicing(self):
        """ Test confirming a vendor invoice to reinvoice cost on the so """
        # force the pricelist to have the same currency as the company
        self.pricelist_usd.currency_id = self.env.ref('base.main_company').currency_id

        serv_cost = self.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 160,
            'list_price': 180,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'PROD_COST',
            'service_type': 'manual',
        })
        prod_gap = self.service_order
        so = self.env['sale.order'].create({
            'partner_id': self.partner_customer_usd.id,
            'partner_invoice_id': self.partner_customer_usd.id,
            'partner_shipping_id': self.partner_customer_usd.id,
            'order_line': [(0, 0, {'name': prod_gap.name, 'product_id': prod_gap.id, 'product_uom_qty': 2, 'product_uom': prod_gap.uom_id.id, 'price_unit': prod_gap.list_price})],
            'pricelist_id': self.pricelist_usd.id,
        })
        so.action_confirm()
        so._create_analytic_account()

        company = self.env.ref('base.main_company')
        journal = self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'STPJ', 'type': 'purchase', 'company_id': company.id})
        invoice_vals = {
            'name': '',
            'type': 'in_invoice',
            'partner_id': self.partner_customer_usd.id,
            'invoice_line_ids': [(0, 0, {'name': serv_cost.name, 'product_id': serv_cost.id, 'quantity': 2, 'uom_id': serv_cost.uom_id.id, 'price_unit': serv_cost.standard_price, 'account_analytic_id': so.analytic_account_id.id, 'account_id': self.account_income.id})],
            'account_id': self.account_payable.id,
            'journal_id': journal.id,
            'currency_id': company.currency_id.id,
        }
        inv = self.env['account.invoice'].create(invoice_vals)
        inv.action_invoice_open()
        sol = so.order_line.filtered(lambda l: l.product_id == serv_cost)
        self.assertTrue(sol, 'Sale: cost invoicing does not add lines when confirming vendor invoice')
        self.assertEquals((sol.price_unit, sol.qty_delivered, sol.product_uom_qty, sol.qty_invoiced), (160, 2, 0, 0), 'Sale: line is wrong after confirming vendor invoice')

    def test_sale_with_pricelist_multi_price_per_product(self):
        """ Test pricelist apply or not on order lines when pricelist on SO """
        # Create the pricelist items
        self.PricelistItem.create({
            'pricelist_id': self.pricelist_with_disct.id,
            'applied_on': '1_product',
            'product_tmpl_id': self.product_order.product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 10
        })
        self.PricelistItem.create({
            'pricelist_id': self.pricelist_with_disct.id,
            'applied_on': '1_product',
            'product_tmpl_id': self.service_deliver.product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 20
        })
        self.PricelistItem.create({
            'pricelist_id': self.pricelist_without_disct.id,
            'applied_on': '1_product',
            'product_tmpl_id': self.service_order.product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 20
        })
        self.PricelistItem.create({
            'pricelist_id': self.pricelist_without_disct.id,
            'applied_on': '1_product',
            'product_tmpl_id': self.product_deliver.product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 10
        })

        # Create an order lines
        self.SaleOrderLine.create({
            'order_id': self.sale_order_pricelist.id,
            'product_id': self.product_order.id
        })
        self.SaleOrderLine.create({
            'order_id': self.sale_order_pricelist.id,
            'product_id': self.service_deliver.id
        })
        self.SaleOrderLine.create({
            'order_id': self.sale_order_pricelist.id,
            'product_id': self.service_order.id
        })
        self.SaleOrderLine.create({
            'order_id': self.sale_order_pricelist.id,
            'product_id': self.product_deliver.id
        })

        # Check that pricelist of the SO has been applied on the sale order lines or not
        for line in self.sale_order_pricelist.order_line:
            if self.sale_order_pricelist.pricelist_id in line.product_id.item_ids.mapped('pricelist_id'):
                for item in self.sale_order_pricelist.pricelist_id.item_ids.filtered(lambda l: l.product_tmpl_id == line.product_id.product_tmpl_id):
                    price = item.percent_price
                    self.assertEquals(price, (line.product_id.list_price - line.price_unit)/line.product_id.list_price*100, 'Pricelist of the SO should be applied on an order line')
            else:
                self.assertEquals(line.price_unit, line.product_id.list_price, 'Pricelist of the SO should not be applied on an order line')

    def test_sale_with_pricelist_formulas(self):
        """ Test SO with the pricelist which one have compute price formula """
        # Add group 'Discount on Lines' to the user
        self.env.user.write({'groups_id': [(4, self.env.ref('sale.group_discount_per_so_line').id)]})
        product_categ = self.env.ref('product.product_category_1')

        # Apply product category on consumable products and also on a peicelist
        with Form(self.product_order) as product:
            product.categ_id = product_categ
        with Form(self.product_deliver) as product:
            product.categ_id = product_categ

        # Create the pricelist items
        self.PricelistItem.create({
            'pricelist_id': self.pricelist_without_disct.id,
            'applied_on': '2_product_category',
            'categ_id': product_categ.id,
            'compute_price': 'formula',
            'base': 'standard_price',
            'price_discount': 15
        })
        self.PricelistItem.create({
            'pricelist_id': self.pricelist_with_disct.id,
            'applied_on': '3_global',
            'compute_price': 'percentage',
            'price_discount': 10
        })

        # Apply pricelist on the SO and create an order lines
        sale_order = Form(self.sale_order_pricelist)
        with sale_order as order:
            order.pricelist_id = self.pricelist_without_disct
            with order.order_line.new() as line:
                line.product_id = self.product_order
            with order.order_line.new() as line:
                line.product_id = self.service_deliver
            with order.order_line.new() as line:
                line.product_id = self.service_order
            with order.order_line.new() as line:
                line.product_id = self.product_deliver
        order = sale_order.save()

        # Check pricelist of the SO apply or not on order lines where pricelist contains formula that add 15% on the cost price
        for line in order.order_line:
            if line.product_id.categ_id in order.pricelist_id.item_ids.mapped('categ_id'):
                for item in order.pricelist_id.item_ids.filtered(lambda l: l.categ_id == line.product_id.categ_id):
                    discount = item.price_discount
                    self.assertEquals(line.discount, discount, 'Pricelist of the SO should be applied on an order line')
                self.assertEquals(line.price_unit, line.product_id.standard_price, 'Pricelist formula should be applied on the cost price')
            else:
                self.assertEquals(line.discount, 0.0, 'Pricelist of SO should not be applied on an order line')
                self.assertEquals(line.price_unit, line.product_id.list_price, 'Unit price of order line should be a sale price as the pricelist not applied on the other category\'s product')

    def test_sale_wtih_taxes(self):
        """ Test SO with taxes """
        # Create a tax with price included
        tax_include = self.env['account.tax'].create({
            'name': 'Tax with price include',
            'amount': 10,
            'price_include': True
        })
        # Create a tax with price not included
        tax_exclude = self.env['account.tax'].create({
            'name': 'Tax with no price include',
            'amount': 10,
        })

        # Apply tax with price included on two products and tax with price not included on other two products
        with Form(self.product_order) as product:
            product.taxes_id.add(tax_include)
        with Form(self.service_deliver) as product:
            product.taxes_id.add(tax_include)
        with Form(self.service_order) as product:
            product.taxes_id.add(tax_exclude)
        with Form(self.product_deliver) as product:
            product.taxes_id.add(tax_exclude)

        # Apply taxes on the sale order lines
        sale_order = Form(self.sale_order)
        with sale_order as order:
            with order.order_line.edit(0) as line:
                line.tax_id.add(tax_include)
            with order.order_line.edit(1) as line:
                line.tax_id.add(tax_include)
            with order.order_line.edit(2) as line:
                line.tax_id.add(tax_exclude)
            with order.order_line.edit(3) as line:
                line.tax_id.add(tax_exclude)
        order = sale_order.save()

        for line in order.order_line:
            if line.tax_id == tax_include:
                price = line.price_unit * line.product_uom_qty - line.price_tax
                self.assertEquals(float_compare(line.price_subtotal, price, precision_digits=2), 0,'Tax should be included on an order line')
            else:
                self.assertEquals(line.price_subtotal, line.price_unit * line.product_uom_qty, 'Tax should not be included on an order line')
        self.assertEquals(order.amount_total, order.amount_untaxed + order.amount_tax, 'Taxes should be applied')
