# -*- coding: utf-8 -*-

import time
from openerp import api, models, _
from common_report_header import common_report_header

class report_partnerbalance(models.AbstractModel, common_report_header):
    _name = 'report.account.report_partnerbalance'

    def lines(self):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        full_account = []
        qry = "SELECT p.ref,l.account_id,ac.name AS account_name,ac.code AS code,p.name, sum(debit) AS debit, sum(credit) AS credit, " \
                    "CASE WHEN sum(debit) > sum(credit) " \
                        "THEN sum(debit) - sum(credit) " \
                        "ELSE 0 " \
                    "END AS sdebit, " \
                    "CASE WHEN sum(debit) < sum(credit) " \
                        "THEN sum(credit) - sum(debit) " \
                        "ELSE 0 " \
                    "END AS scredit, " \
                    "(SELECT sum(debit-credit) " \
                        "FROM " + self.tables + \
                        " WHERE partner_id = p.id " \
                            "AND blocked = TRUE " + self.filters + \
                    " ) AS enlitige " \
            "FROM " + self.tables + " LEFT JOIN res_partner p ON (account_move_line.partner_id=p.id) " \
            "JOIN account_account ac ON (account_move_line.account_id = ac.id)" \
            "WHERE ac.internal_type IN %s " + self.filters + \
            " GROUP BY p.id, p.ref, p.name,account_move_line.account_id,ac.name,ac.code " \
            "ORDER BY account_move_line.account_id,p.name"
        p = (tuple(self.ACCOUNT_TYPE), ) + tuple(self.where_params)

        self._cr.execute(qry, p)
        res = self._cr.dictfetchall()


        if self.display_partner == 'non-zero_balance':
            full_account = [r for r in res if r['sdebit'] > 0 or r['scredit'] > 0]
        else:
            full_account = [r for r in res]

        for rec in full_account:
            if not rec.get('name', False):
                rec.update({'name': _('Unknown Partner')})

        ## We will now compute Total
        subtotal_row = self._add_subtotal(full_account)
        return subtotal_row

    def _add_subtotal(self, cleanarray):
        i = 0
        completearray = []
        tot_debit = 0.0
        tot_credit = 0.0
        tot_scredit = 0.0
        tot_sdebit = 0.0
        tot_enlitige = 0.0
        for r in cleanarray:
            # For the first element we always add the line
            # type = 1 is the line is the first of the account
            # type = 2 is an other line of the account
            if i==0:
                # We add the first as the header
                #
                ##
                new_header = {}
                new_header['ref'] = ''
                new_header['name'] = r['account_name']
                new_header['code'] = r['code']
                new_header['debit'] = r['debit']
                new_header['credit'] = r['credit']
                new_header['scredit'] = tot_scredit
                new_header['sdebit'] = tot_sdebit
                new_header['enlitige'] = tot_enlitige
                new_header['balance'] = r['debit'] - r['credit']
                new_header['type'] = 3
                ##
                completearray.append(new_header)
                #
                r['type'] = 1
                r['balance'] = float(r['sdebit']) - float(r['scredit'])

                completearray.append(r)
                #
                tot_debit = r['debit']
                tot_credit = r['credit']
                tot_scredit = r['scredit']
                tot_sdebit = r['sdebit']
                tot_enlitige = (r['enlitige'] or 0.0)
                #
            else:
                if cleanarray[i]['account_id'] <> cleanarray[i-1]['account_id']:

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3
                    # we reset the counter
                    tot_debit = r['debit']
                    tot_credit = r['credit']
                    tot_scredit = r['scredit']
                    tot_sdebit = r['sdebit']
                    tot_enlitige = (r['enlitige'] or 0.0)
                    #
                    ##
                    new_header = {}
                    new_header['ref'] = ''
                    new_header['name'] = r['account_name']
                    new_header['code'] = r['code']
                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3
                    ##get_fiscalyear
                    ##

                    completearray.append(new_header)
                    ##
                    #
                    r['type'] = 1
                    #
                    r['balance'] = float(r['sdebit']) - float(r['scredit'])

                    completearray.append(r)

                if cleanarray[i]['account_id'] == cleanarray[i-1]['account_id']:
                    # we reset the counter

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3

                    tot_debit = tot_debit + r['debit']
                    tot_credit = tot_credit + r['credit']
                    tot_scredit = tot_scredit + r['scredit']
                    tot_sdebit = tot_sdebit + r['sdebit']
                    tot_enlitige = tot_enlitige + (r['enlitige'] or 0.0)

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)

                    #
                    r['type'] = 2
                    #
                    r['balance'] = float(r['sdebit']) - float(r['scredit'])
                    #

                    completearray.append(r)

            i = i + 1
        return completearray

    def _get_partners(self):

        if self.result_selection == 'customer':
            return _('Receivable Accounts')
        elif self.result_selection == 'supplier':
            return _('Payable Accounts')
        elif self.result_selection == 'customer_supplier':
            return _('Receivable and Payable Accounts')
        return ''



    @api.multi
    def render_html(self, data):
        print"\n\n\n\ninside...............renderrrrrrr"
        report_obj = self.env['report']
        self.model = self._context.get('active_model')
        MoveLine = self.env['account.move.line']
        docs = self.env[self.model].browse(self._context.get('active_id'))
        print"\n\n\n\ndaaaataaaaa...",data['options']['form']
        self.ctx = data['options']['form'].get('used_context',{}).copy()
        self.tables, self.where_clause, self.where_params = MoveLine.with_context(self.ctx)._query_get()
        print ">>tables>>>>>>>>>>>>>>",self.tables
        print"\n\nelf.where_clause",self.where_clause, "\n\n\nself.where_params",self.where_params
        
        self.tables = self.tables.replace('"','') if self.tables else "account_move_line"
        self.wheres = [""]
        if self.where_clause.strip():
            self.wheres.append(self.where_clause.strip())
        self.filters = " AND ".join(self.wheres)
        print"filtrrrss",self.filters

        self.display_partner = data['options']['form'].get('display_partner', 'non-zero_balance')
        self.result_selection = data['options']['form'].get('result_selection')
        self.target_move = data['options']['form'].get('target_move', 'all')

        if (self.result_selection == 'customer' ):
            self.ACCOUNT_TYPE = ('receivable',)
        elif (self.result_selection == 'supplier'):
            self.ACCOUNT_TYPE = ('payable',)
        else:
            self.ACCOUNT_TYPE = ('payable', 'receivable')

        self._cr.execute("SELECT a.id " \
                "FROM account_account a " \
                    "WHERE a.internal_type IN %s ", (self.ACCOUNT_TYPE,))
        self.account_ids = [a for (a,) in self._cr.fetchall()]
        lines = self.lines()
        sum_debit = sum_credit = sum_litige = 0
        for line in filter(lambda x: x['type'] == 3, lines):
            sum_debit += line['debit'] or 0
            sum_credit += line['credit'] or 0
            sum_litige += line['enlitige'] or 0

        self.account_ids = []
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['options']['form'],
            'docs': docs,
            'time': time,
            'get_journal': self._get_journal,
            'get_filter': self._get_filter,
            'get_account': self._get_account,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_partners':self._get_partners,
            'get_target_move': self._get_target_move,
            'lines': lambda: lines,
            'sum_debit': lambda: sum_debit,
            'sum_credit': lambda: sum_credit,
            'sum_litige': lambda: sum_litige,
        }
        print"\n\n\ndocargs",docargs
        return report_obj.render('account.report_partnerbalance', docargs)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
