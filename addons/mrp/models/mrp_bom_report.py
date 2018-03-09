# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import api, models
from odoo.tools import config, float_round


class MrpBomReport(models.TransientModel):
    _name = 'mrp.bom.report'
    _description = "Mrp Bom Report"

    def _get_operations(self, bom, product, parent, qty, bom_ids):
        operations = []
        if parent:
            qty = parent.product_uom_id._compute_quantity(qty, bom.product_uom_id, round=False)
        for line in bom.bom_line_ids:
            if line._skip_bom_line(product):
                continue
            line_quantity = line.product_qty * qty
            if parent:
                line_quantity = line.product_qty * qty
            if line.bom_id.routing_id and line.bom_id.id not in bom_ids:
                bom_ids.append(line.bom_id.id)
                operations = self._get_operation_line(line.bom_id.routing_id, line.bom_id, parent, (qty / bom.product_qty))
            if line.child_bom_id:
                qty = line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id, round=False)
                _operations = self._get_operations(line.child_bom_id, line.product_id, line, qty, bom_ids)
                operations += _operations
        return operations

    def _get_operation_line(self, routing, bom, parent, qty):
        operations = []
        total = 0.0
        for operation in routing.operation_ids:
            rounding = bom.product_uom_id.rounding
            cycle_number = float_round((1.0 / operation.workcenter_id.capacity), precision_rounding=rounding)
            if not parent:
                cycle_number = cycle_number * qty
            duration_expected = cycle_number * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency
            if parent:
                duration_expected = duration_expected * qty
            duration_expected += operation.workcenter_id.time_stop + operation.workcenter_id.time_start
            total = ((duration_expected / 60.0) * operation.workcenter_id.costs_hour)
            operations.append({
                'operation': operation,
                'name': operation.name + ' - ' + bom.product_tmpl_id.name,
                'duration_expected': duration_expected,
                'total': float_round(total, precision_rounding=rounding),
            })
        return operations

    def _get_price(self, bom, factor):
        price = 0
        for line in bom.bom_line_ids:
            if line.child_bom_id:
                qty = line.product_uom_id._compute_quantity(line.product_qty * factor, line.child_bom_id.product_uom_id)
                sub_price = self._get_price(line.child_bom_id, qty)
                price += sub_price * qty
            else:
                prod_qty = line.product_qty * factor
                price += (line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * prod_qty)
        return price

    @api.model
    def get_lines(self, bom_id=False, line_qty=False, line_id=False, level=False):
        context = self.env.context or {}
        lines = {}
        bom = self.env['mrp.bom'].browse(bom_id or context.get('active_id'))
        bom_quantity = float(context.get('searchQty') or 0) or bom.product_qty
        bom_product_variants = {}
        bom_uom_name = ''
        if line_id:
            current_line = self.env['mrp.bom.line'].browse(int(line_id))
            bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)
        if bom:
            bom_uom_name = bom.product_uom_id.name

            # Get variants used for search
            if not bom.product_id:
                for variant in bom.product_tmpl_id.product_variant_ids:
                    bom_product_variants[variant.id] = variant.display_name

            # Display bom components for current selected product variant
            if context.get('searchVariant'):
                product = self.env['product.product'].browse(int(context.get('searchVariant')))
            else:
                product = bom.product_id or bom.product_tmpl_id.product_variant_id

            components = []
            operations_data = self._get_operations(bom, product, False, bom_quantity, [])
            lines = {
                'bom': bom,
                'bom_qty': bom_quantity,
                'bom_prod_name': product.display_name,
                'currency': self.env.user.company_id.currency_id,
                'product': product,
                'total': 0.0,
                'operations': operations_data,
                'operations_total': sum([op['total'] for op in operations_data])
            }
            for line in bom.bom_line_ids:
                line_quantity = (bom_quantity) * line.product_qty
                if line._skip_bom_line(product):
                    continue
                if line.child_bom_id:
                    factor = line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id) * line.child_bom_id.product_qty
                    price = self._get_price(line.child_bom_id, factor) / line_quantity
                else:
                    price = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id)
                prod_qty = line_quantity
                total = prod_qty * price
                components.append({
                    'prod_id': line.product_id.id,
                    'prod_name': line.product_id.display_name,
                    'prod_qty': line_quantity,
                    'prod_uom': line.product_uom_id.name,
                    'prod_cost': price,
                    'parent_id': bom_id,
                    'line_id': line.id,
                    'total': total,
                    'child_bom': line.child_bom_id.id,
                    'level': level or 0
                })
                lines['total'] += total
            lines['components'] = components
        return {
            'lines': lines,
            'variants': bom_product_variants,
            'bom_uom_name': bom_uom_name,
            'bom_qty': bom_quantity,
            'is_variant_applied': self.env.user.user_has_groups('product.group_product_variant'),
            'is_uom_applied': self.env.user.user_has_groups('uom.group_uom')
        }

    @api.model
    def get_html(self, given_context=None, bom_id=False, line_qty=False, line_id=False, level=False):
        res = self.with_context(given_context).get_lines(bom_id, line_qty, line_id, level)
        template = 'mrp.report_mrp_bom'
        # Render particular bom line
        if bom_id:
            template = 'mrp.report_mrp_bom_line'
        res['lines'] = self.env.ref(template).render({'data': res['lines']})
        return res

    @api.model
    def get_pdf(self, bom_id):
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)
        datas = self.with_context(print_mode=True)._get_pdf_lines(bom_id)
        report_values = {
            'mode': 'print',
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
        }
        IrActionsReport = self.env['ir.actions.report']
        body = self.env['ir.ui.view'].render_template('mrp.report_mrp_bom_pdf', values=dict(report_values, datas=[datas], report=self, context=self))
        header = IrActionsReport.render_template('web.internal_layout', values=report_values)
        header = IrActionsReport.render_template('web.minimal_layout', values=dict(report_values, subst=True, body=header))
        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body], header=header, landscape=True,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )

    def _get_pdf_lines(self, bom_id):
        child_bom_ids = json.loads(self.env.context.get('child_bom_ids'))
        res = self.get_lines(bom_id)
        data = {}
        if res:
            lines = res['lines']
            body = {}
            counter = 0
            data['header'] = {
                'bom': lines['bom'],
                'bom_qty': lines['bom_qty'],
                'bom_prod_name': lines['bom_prod_name'],
                'currency': lines['currency'],
                'total': lines['total'],
                'operations': lines['operations'],
                'operations_total': lines['operations_total'],
            }
            for component in lines['components']:
                body[counter] = dict(component)
                body[counter]['expanded'] = False

                if component.get('child_bom') in child_bom_ids:
                    body[counter]['expanded'] = True
                    sub_lines, counter = self._get_pdf_child_lines(component['child_bom'], component['prod_qty'], component['level'], counter, child_bom_ids)
                    body.update(sub_lines)
                counter += 1
            data['body'] = body
        return data

    def _get_pdf_child_lines(self, bom_id, bom_qty, level, counter, child_bom_ids):
        data = {}
        lines = self.get_lines(bom_id, bom_qty, False, level + 1)

        for line in lines['lines']['components']:
            counter += 1
            data[counter] = dict(line)
            data[counter]['expanded'] = False

            if line.get('child_bom') in child_bom_ids:
                data[counter]['expanded'] = True
                sub_lines, counter = self._get_pdf_child_lines(line['child_bom'], line['prod_qty'], line['level'], counter, child_bom_ids)
                data.update(sub_lines)
        return data, counter
