# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = "res.company"

    propagation_minimum_delta = fields.Integer('Minimum Delta for Propagation of a Date Change on moves linked together', default=1)
    internal_transit_location_id = fields.Many2one(
        'stock.location', 'Internal Transit Location', on_delete="restrict",
        help="Technical field used for resupply routes between warehouses that belong to this company")

    def create_transit_location(self):
        '''Create a transit location with company_id being the given company_id. This is needed
           in case of resuply routes between warehouses belonging to the same company, because
           we don't want to create accounting entries at that time.
        '''
        # TDE FIXME: called in data - should be done in init ??
        parent_location = self.env.ref('stock.stock_location_locations', raise_if_not_found=False)
        for company in self:
            location = self.env['stock.location'].create({
                'name': _('%s: Transit Location') % company.name,
                'usage': 'transit',
                'location_id': parent_location and parent_location.id or False,
            })
            if not self.env['stock.warehouse'].search([('company_id', '=', company.id)]):
                warehouse = self.env['stock.warehouse'].create({
                    'name': company.name,
                    'code': company.name[:5],
                    'company_id': company.id,
                    'partner_id': company.partner_id.id
                })
            location.sudo().write({'company_id': company.id})
            company.write({'internal_transit_location_id': location.id})

    @api.model
    def create(self, vals):
        company = super(Company, self).create(vals)

        # multi-company rules prevents creating warehouse and sub-locations
        self.env['stock.warehouse'].check_access_rights('create')
        company.create_transit_location()
        return company
