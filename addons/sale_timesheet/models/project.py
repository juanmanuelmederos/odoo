# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Line', domain=[('is_expense', '=', False)], readonly=True, help="Sale order line from which the project has been created. Used for tracability.")
    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", default='no', required=True, help='Billable type implies:\n'
        ' - At task rate: each time spend on a task is billed at task rate.\n'
        ' - No Billable: track time without invoicing it')

    @api.constrains('billable_type', 'sale_line_id')
    def _check_billable_type(self):
        for project in self:
            if not project.sale_line_id and project.billable_type != 'no':
                raise ValidationError(_("A billable project should be linked to a Sales Order Item."))

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        if self.allow_timesheets:
            return self.action_view_timesheet_plan()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets of %s') % self.name,
            'domain': [('project_id', '!=', False)],
            'res_model': 'account.analytic.line',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    Record timesheets
                </p><p>
                    You can register and track your workings hours by project every
                    day. Every time spent on a project will become a cost and can be re-invoiced to
                    customers if required.
                </p>
            """),
            'limit': 80,
            'context': {
                'default_project_id': self.id,
                'search_default_project_id': [self.id]
            }
        }

    @api.multi
    def action_view_timesheet_plan(self):
        action = self.env.ref('sale_timesheet.project_timesheet_action_client_timesheet_plan').read()[0]
        action['params'] = {
            'project_ids': self.ids,
        }
        action['context'] = {
            'active_id': self.id,
            'active_ids': self.ids,
            'search_default_name': self.name,
        }
        return action


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _get_default_partner(self):
        partner = super(ProjectTask, self)._get_default_partner()
        if 'default_project_id' in self.env.context:  # partner from SO line is prior on one from project
            project = self.env['project.project'].browse(self.env.context['default_project_id'])
            partner = project.sale_line_id.order_partner_id
        return partner

    @api.model
    def _default_sale_line_id(self):
        if 'default_project_id' in self.env.context:
            project = self.env['project.project'].browse(self.env.context['default_project_id'])
            if project.billable_type != 'no':
                return project.sale_line_id

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', default=_default_sale_line_id, domain="[('is_service', '=', True), ('order_partner_id', '=', partner_id), ('is_expense', '=', False)]")
    sale_order_id = fields.Many2one('sale.order', 'Sales Order', related='sale_line_id.order_id', store=True, readonly=True)
    billable_type = fields.Selection([
        ('task_rate', 'At Task Rate'),
        ('no', 'No Billable')
    ], string="Billable Type", default='no', required=True, readonly=True)

    @api.onchange('project_id')
    def _onchange_project(self):
        result = super(ProjectTask, self)._onchange_project()
        if self.project_id:
            self.sale_line_id = self.project_id.sale_line_id
            if not self.partner_id:
                self.partner_id = self.sale_line_id.order_partner_id
        return result

    @api.multi
    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for task in self:
            if task.sale_line_id:
                if not task.sale_line_id.is_service or task.sale_line_id.is_expense:
                    raise ValidationError(_("The Sales order line should be one selling a service, and no coming from expense."))

    @api.multi
    @api.constrains('billable_type', 'sale_line_id')
    def _check_billable_type(self):
        for task in self:
            if task.sale_line_id and task.billable_type == 'no':
                raise ValidationError(_("A billable task should be linked to a sale order item."))

    @api.model
    def create(self, values):
        # sub task has the same so line and billable type as their parent
        if 'parent_id' in values and values['parent_id']:
            parent_task_sudo = self.env['project.task'].browse(values['parent_id']).sudo()
            values['sale_line_id'] = parent_task_sudo.sale_line_id.id
            values['billable_type'] = parent_task_sudo.billable_type
        # determine billable type from the project
        if not values.get('billable_type'):
            values['billable_type'] = self.env['project.project'].browse(values['project_id']).billable_type
        return super(ProjectTask, self).create(values)

    @api.multi
    def write(self, values):
        """ NOTE: changing task from project does not modify its billable type. """
        # sub task has the same so line than their parent
        if 'parent_id' in values and values['parent_id']:
            parent_task_sudo = self.env['project.task'].browse(values['parent_id']).sudo()
            values['sale_line_id'] = parent_task_sudo.sale_line_id.id
            values['billable_type'] = parent_task_sudo.billable_type

        result = super(ProjectTask, self).write(values)
        # reassign SO line on related timesheet lines
        if 'sale_line_id' in values:
            self.sudo().mapped('timesheet_ids').write({
                'so_line': values['sale_line_id']
            })
        return result

    @api.multi
    def unlink(self):
        if any(task.sale_line_id for task in self):
            raise ValidationError(_('You cannot delete a task related to a Sales Order. You can only archive this task.'))
        return super(ProjectTask, self).unlink()

    @api.multi
    def _subtask_implied_fields(self):
        fields_list = super(ProjectTask, self)._subtask_implied_fields()
        fields_list += ['sale_line_id', 'billable_type']
        return fields_list

    @api.multi
    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    def rating_get_partner_id(self):
        partner = self.partner_id or self.sale_line_id.order_id.partner_id
        if partner:
            return partner
        return super(ProjectTask, self).rating_get_partner_id()
