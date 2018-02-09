# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, AccessError

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestAccountEntry(TestExpenseCommon):
    """
    Check journal entries when the expense product is having tax which is tax included.
    """

    def setUp(self):
        super(TestAccountEntry, self).setUp()

        self.setUpAdditionalAccounts()

        self.product_expense = self.env['product.product'].create({
            'name': "Delivered at cost",
            'standard_price': 700,
            'list_price': 700,
            'type': 'consu',
            'supplier_taxes_id': [(6, 0, [self.tax.id])],
            'default_code': 'CONSU-DELI-COST',
            'taxes_id': False,
            'property_account_expense_id': self.account_expense.id,
        })

    def test_account_entry(self):
        """ Checking accounting move entries and analytic entries when submitting expense """
        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.employee.id,
        })
        expense_line = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.employee.id,
            'product_id': self.product_expense.id,
            'unit_amount': 700.00,
            'tax_ids': [(6, 0, [self.tax.id])],
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account.id,
        })
        expense_line._onchange_product_id()
        # Submitted to Manager
        self.assertEquals(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_sheet()
        self.assertEquals(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEquals(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # [(line.debit, line.credit, line.tax_line_id.id) for line in self.expense.expense_line_ids.account_move_id.line_ids]
        # should git this result [(0.0, 700.0, False), (63.64, 0.0, 179), (636.36, 0.0, False)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEquals(line.credit, 700.00)
                self.assertEquals(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEquals(line.debit, 636.36)
                    self.assertEquals(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEquals(line.product_id, self.product_expense, "Product of debit move line should be the one from the expense")
                else:
                    self.assertAlmostEquals(line.debit, 63.64)
                    self.assertEquals(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

        self.assertEquals(self.analytic_account.line_ids, expense.account_move_id.mapped('line_ids.analytic_line_ids'))
        self.assertEquals(len(self.analytic_account.line_ids), 1, "Analytic Account should have only one line")
        self.assertAlmostEquals(self.analytic_account.line_ids[0].amount, -636.36, "Amount on the only AAL is wrong")
        self.assertEquals(self.analytic_account.line_ids[0].product_id, self.product_expense, "Product of AAL should be the one from the expense")


class TestExpenseRights(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super(TestExpenseRights, cls).setUpClass()

        Users = cls.env['res.users'].with_context(no_reset_password=True)
        Departments = cls.env['hr.department']
        Employees = cls.env['hr.employee']
        Products = cls.env['product.product']

        cls.Expenses = cls.env['hr.expense']
        cls.Expense_sheets = cls.env['hr.expense.sheet']

        # Find Employee group
        group_employee_id = cls.env.ref('base.group_user').id

        cls.user_emp = Users.create({
            'name': 'Robin Employee',
            'login': 'robin',
            'email': 'robin@example.com',
            'groups_id': [(6, 0, [group_employee_id])]
        })

        cls.user_emp2 = Users.create({
            'name': 'Superboy Employee',
            'login': 'superboy',
            'email': 'superboy@example.com',
            'groups_id': [(6, 0, [group_employee_id])]
        })

        cls.user_officer = Users.create({
            'name': 'Batman Officer',
            'login': 'batman',
            'email': 'batman.hero@example.com',
            'groups_id': [(6, 0, [group_employee_id, cls.env.ref('hr_expense.group_hr_expense_user').id])]
        })

        cls.user_manager = Users.create({
            'name': 'Superman Manager',
            'login': 'superman',
            'email': 'superman.hero@example.com',
            'groups_id': [(6, 0, [group_employee_id, cls.env.ref('hr_expense.group_hr_expense_manager').id])]
        })

        cls.emp_emp = Employees.create({
            'name': 'Robin',
            'user_id': cls.user_emp.id,
        })

        cls.emp_emp2 = Employees.create({
            'name': 'Superboy',
            'user_id': cls.user_emp2.id,
        })

        cls.emp_officer = Employees.create({
            'name': 'Batman',
            'user_id': cls.user_officer.id,
        })

        cls.emp_manager = Employees.create({
            'name': 'Superman',
            'user_id': cls.user_manager.id,
        })

        cls.rd = Departments.create({
            'name': 'R&D',
            'manager_id': cls.emp_officer.id,
            'member_ids': [(6, 0, [cls.emp_emp.id])],
        })

        cls.ps = Departments.create({
            'name': 'PS',
            'manager_id': cls.emp_manager.id,
            'member_ids': [(6, 0, [cls.emp_emp2.id])],
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit').id
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen').id

        cls.product_1 = Products.create({
            'name': 'Batmobile repair',
            'type': 'service',
            'uom_id': cls.uom_unit,
            'uom_po_id': cls.uom_unit,
        })

        cls.product_2 = Products.create({
            'name': 'Superboy costume washing',
            'type': 'service',
            'uom_id': cls.uom_unit,
            'uom_po_id': cls.uom_unit,
        })

    def test_expense_create(self):
        # Employee should be able to create an Expense
        self.Expenses.sudo(self.user_emp.id).create({
            'name': 'Batmobile repair',
            'employee_id': self.emp_emp.id,
            'product_id': self.product_1.id,
            'unit_amount': 1,
            'quantity': 1,
        })

        # Employee should not be able to create an Expense for someone else
        with self.assertRaises(AccessError):
            self.Expenses.sudo(self.user_emp.id).create({
                'name': 'Superboy costume washing',
                'employee_id': self.emp_emp2.id,
                'product_id': self.product_2.id,
                'unit_amount': 1,
                'quantity': 1,
            })

    def test_expense_approve(self):
        sheet = self.Expense_sheets.create({
            'name': 'Furnitures',
            'employee_id': self.emp_officer.id,
        })

        sheet_2 = self.Expense_sheets.create({
            'name': 'Services',
            'employee_id': self.emp_emp.id,
        })

        sheet_3 = self.Expense_sheets.create({
            'name': 'Services 2',
            'employee_id': self.emp_emp2.id,
        })

        # Employee should not be able to approve expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_officer).approve_sheet()
        # Officer should not be able to approve own expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_officer).approve_sheet()
        sheet.sudo(self.user_manager).approve_sheet()

        # Officer should be able to approve expense from his department
        sheet_2.sudo(self.user_officer).approve_sheet()

        # Officer should not be able to approve expense sheet from another department
        with self.assertRaises(AccessError):
            sheet_3.sudo(self.user_officer).approve_sheet()
        sheet_3.sudo(self.user_manager).approve_sheet()

    def test_expense_refuse(self):
        sheet = self.Expense_sheets.create({
            'name': 'Furnitures',
            'employee_id': self.emp_officer.id,
        })

        sheet_2 = self.Expense_sheets.create({
            'name': 'Services',
            'employee_id': self.emp_emp.id,
        })

        sheet_3 = self.Expense_sheets.create({
            'name': 'Services 2',
            'employee_id': self.emp_emp2.id,
        })

        sheet.sudo(self.user_manager).approve_sheet()
        sheet_2.sudo(self.user_manager).approve_sheet()
        sheet_3.sudo(self.user_manager).approve_sheet()

        # Employee should not be able to refuse expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_emp).refuse_sheet('')
        # Officer should not be able to refuse own expense sheet
        with self.assertRaises(UserError):
            sheet.sudo(self.user_officer).refuse_sheet('')
        sheet.sudo(self.user_manager).refuse_sheet('')

        # Officer should be able to refuse expense from his department
        sheet_2.sudo(self.user_officer).refuse_sheet('')

        # Officer should not be able to refuse expense sheet from another department
        with self.assertRaises(AccessError):
            sheet_3.sudo(self.user_officer).refuse_sheet('')
        sheet_3.sudo(self.user_manager).refuse_sheet('')
