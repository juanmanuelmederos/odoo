# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_account_bank_cash = fields.Boolean(string='Bank & Cash')
    kpi_account_bank_cash_value = fields.Monetary(compute='_compute_kpi_account_total_revenue_value')
    kpi_account_total_revenue = fields.Boolean(string='Revenue')
    kpi_account_total_revenue_value = fields.Monetary(compute='_compute_kpi_account_total_revenue_value')

    @api.depends('start_date', 'end_date')
    def _compute_kpi_account_total_revenue_value(self):
        sale_journal_ids = self.env['account.journal'].search([('type', '=', 'sale')]).ids
        bank_cash_journal_ids = self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])]).ids

        def _account_move_amount(journal_ids):
            return sum([account_move['amount'] for account_move in account_moves if account_move['journal_id'][0] in journal_ids])

        context = self._context
        for record in self:
            date_domain = [("create_date", ">=", record.start_date), ("create_date", "<=", record.end_date)]
            if context.get('timeframe') == 'yesterday':
                date_domain = [("create_date", ">=", record.start_date), ("create_date", "<", record.end_date)]
            date_domain += [('journal_id.type', 'in', ['sale', 'cash', 'bank']), ('company_id', '=', context.get('company_id').id)]
            account_moves = self.env['account.move'].read_group(date_domain, ['journal_id', 'amount'], ['journal_id'])
            record.kpi_account_total_revenue_value = _account_move_amount(sale_journal_ids)
            record.kpi_account_bank_cash_value = _account_move_amount(bank_cash_journal_ids)
