# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _name = 'project.product.employee.map'

    @api.model
    def _default_project_id(self):
        if self._context.get('active_id'):
            return self._context['active_id']
        return False

    project_id = fields.Many2one('project.project', "Project", domain=[('billable_type', '!=', 'no')], requried=True, default=_default_project_id)
    employee_id = fields.Many2one('hr.employee', "Employee", requried=True)
    product_id = fields.Many2one('product.product', "Product", domain=[('type', '=', 'service')], requried=True)

    _sql_constraints = [
        ('uniq_map_product_employee_per_project', 'UNIQUE(project_id,employee_id,product_id)', 'You can only map one employee with product per project.'),
    ]
