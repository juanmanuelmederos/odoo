# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id')
    iface_tax_included = fields.Selection([('subtotal', 'Tax-Excluded Price'), ('total', 'Tax-Included Price')], related="company_id.iface_tax_included", required=True)
    use_pricelist = fields.Boolean("Use a pricelist.", config_parameter='point_of_sale.use_pricelist')
    group_sale_pricelist = fields.Boolean("Use pricelists to adapt your price per customers",
                                          implied_group='product.group_sale_pricelist',
                                          help="""Allows to manage different prices based on rules per category of customers.
                    Example: 10% for retailers, promotion of 5 EUR on this product, etc.""")
    group_pricelist_item = fields.Boolean("Show pricelists to customers",
                                          implied_group='product.group_pricelist_item')
    pricelist_id = fields.Many2one('product.pricelist', related='company_id.pricelist_id', string='Default Pricelist', required=True,
        help="The pricelist used if no customer is selected or if the customer has no Sale Pricelist configured.")
    available_pricelist_ids = fields.Many2many('product.pricelist', related='company_id.available_pricelist_ids', string='Available Pricelists',
        help="Make several pricelists available in the Point of Sale. You can also apply a pricelist to specific customers from their contact form (in Sales tab). To be valid, this pricelist must be listed here as an available pricelist. Otherwise the default pricelist will apply.")
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments", help="The transactions are processed by Vantiv. Set your Vantiv credentials on the related payment journal.")

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([('currency_id', '=', self.env.user.company_id.currency_id.id)], limit=1)

    @api.constrains('pricelist_id', 'available_pricelist_ids')
    def _check_currencies(self):
        if self.pricelist_id not in self.available_pricelist_ids:
            raise ValidationError(_("The default pricelist must be included in the available pricelists."))
        if any(self.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != self.currency_id)):
            raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                    " as the Sales Journal set on this point of sale if you use"
                                    " the Accounting application."))
