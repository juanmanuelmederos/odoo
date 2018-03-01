# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCreateInvoice(models.TransientModel):
    _name = 'project.create.invoice'
    _description = "Create a Invoice from project"

    @api.model
    def default_get(self, fields):
        result = super(ProjectCreateInvoice, self).default_get(fields)
        active_id = self._context.get('active_id')
        if 'project_id' in fields and active_id:
            result['project_id'] = active_id
        return result

    project_id = fields.Many2one('project.project', "Project", help="Project to make billable")
    sale_order_id = fields.Many2one('sale.order', string="Choose the Sales Order to invoice")

    @api.onchange('project_id')
    def _onchange_project_id(self):
        sale_orders = self.project_id.tasks.mapped('sale_line_id.order_id').filtered(lambda so: so.invoice_status == 'to invoice')
        return {
            'domain': {'sale_order_id': [('id', 'in', sale_orders.ids)]},
        }

    @api.multi
    def action_create_invoice(self):
        if self.sale_order_id.invoice_status != 'to invoice':
            raise UserError(_("The selected Sales Order should contain something to invoice."))
        action = self.env.ref('sale.action_view_sale_advance_payment_inv').read()[0]
        action['context'] = {
            'active_ids': self.sale_order_id.ids
        }
        return action
