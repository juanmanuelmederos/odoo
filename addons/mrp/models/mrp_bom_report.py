# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import config


class MrpBomReport(models.TransientModel):
    _name = 'mrp.bom.report'
    _description = "Mrp Bom Report"

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
        datas = []
        bom = self.env['mrp.bom'].browse(bom_id or context.get('active_id'))
        qty = float(context.get('searchQty', 0)) or bom.product_qty
        bom_quantity = qty
        variants = {}
        bom_uom_name = ''
        if line_id:
            current_line = self.env['mrp.bom.line'].browse(int(line_id))
            bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)
        if bom:
            bom_uom_name = bom.product_uom_id.name
            if not bom.product_id and bom.product_tmpl_id:
                for i in bom.product_tmpl_id.product_variant_ids:
                    variants[i.id] = i.display_name
            products = bom.product_id or bom.product_tmpl_id.product_variant_id
            if context.get('searchVariant'):
                products = self.env['product.product'].browse(int(context.get('searchVariant')))
            for product in products:
                lines = {}
                components = []
                lines.update({
                    'bom': bom,
                    'bom_qty': bom_quantity,
                    'bom_prod_name': product.display_name,
                    'currency': self.env.user.company_id.currency_id,
                    'product': product,
                    'total': 0.0
                })
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
                lines['components'] and datas.append(lines)
        return {'datas': datas, 'variants': variants, 'bom_uom_name': bom_uom_name}

    @api.model
    def get_html(self, given_context=None, bom_id=False, line_qty=False, line_id=False, level=False):
        rcontext = {}
        call = self.with_context(given_context).get_lines(bom_id, line_qty, line_id, level)
        rcontext['datas'] = call['datas']
        if bom_id:
            rcontext['data'] = rcontext['datas'][0]
            return {'html': self.env.ref('mrp.report_mrp_bom_line').render(rcontext), 'variants': call['variants'], 'bom_uom_name': call['bom_uom_name']}
        else:
            return {'html': self.env.ref('mrp.report_mrp_bom').render(rcontext), 'variants': call['variants'], 'bom_uom_name': call['bom_uom_name']}

    @api.model
    def get_pdf(self, bom_id, child_bom_ids):
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        datas = self.with_context(print_mode=True)._get_pdf_lines(bom_id, child_bom_ids)
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
        }
        body = self.env['ir.ui.view'].render_template(
            "mrp.report_mrp_bom_pdf",
            values=dict(rcontext, datas=datas, report=self, context=self),
        )

        header = self.env['ir.actions.report'].render_template("web.internal_layout", values=rcontext)
        header = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=header))

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body], header=header, landscape=True,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )

    def _get_pdf_lines(self, bom_id, child_bom_ids):
        final_data = []
        lines = self.get_lines(bom_id)['datas']

        for line in lines:
            data = {}
            body = {}
            counter = 0
            data['header'] = {
                'bom': line['bom'],
                'bom_prod_name': line['bom_prod_name'],
                'currency': line['currency'],
                'total': line['total'],
            }

            for component in line['components']:
                body[counter] = dict(component)
                body[counter]['expanded'] = False

                if component.get('child_bom') in child_bom_ids:
                    body[counter]['expanded'] = True
                    sub_lines, counter = self._get_pdf_child_lines(component['child_bom'], component['prod_qty'], component['level'], counter, child_bom_ids)
                    body.update(sub_lines)
                counter += 1
            data['body'] = body
            data['body'] and final_data.append(data)
        return final_data

    def _get_pdf_child_lines(self, bom_id, bom_qty, level, counter, child_bom_ids):
        data = {}
        lines = self.get_lines(bom_id, bom_qty, level + 1)

        for line in lines[0]['components']:
            counter += 1
            data[counter] = dict(line)
            data[counter]['expanded'] = False

            if line.get('child_bom') in child_bom_ids:
                data[counter]['expanded'] = True
                sub_lines, counter = self._get_pdf_child_lines(line['child_bom'], line['prod_qty'], line['level'], counter, child_bom_ids)
                data.update(sub_lines)
        return data, counter
