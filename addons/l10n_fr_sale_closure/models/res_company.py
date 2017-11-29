# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_closure_sequence_id = fields.Many2one('ir.sequence', 'Sequence to use to build sale closures', readonly=True)

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if self._is_accounting_unalterable():
            sequence_fields = ['l10n_fr_closure_sequence_id']
            company._create_secure_sequence(sequence_fields)
        return company

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_closure_sequence_id']
                company._create_secure_sequence(sequence_fields)
        return res
