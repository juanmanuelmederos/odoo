# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class ReportStockForecat(models.Model):
    _name = 'report.stock.forecast'
    _auto = False

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', readonly=True)
    cumulative_quantity = fields.Float(string='Cumulative Quantity', readonly=True)
    quantity = fields.Float(readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_forecast')
        self._cr.execute("""CREATE or REPLACE VIEW report_stock_forecast AS (SELECT
        row_number() OVER (ORDER BY id desc) AS id,
        product_id as product_id,
        date as date,
        sum(product_qty) AS quantity,
        sum(sum(product_qty)) OVER (PARTITION BY product_id ORDER BY id desc) AS cumulative_quantity,
        reference,
        company_id
        FROM
        (SELECT
        MIN(id) as id,
        MAIN.product_id as product_id,
        SUB.date as date,
        CASE WHEN MAIN.date = SUB.date THEN sum(MAIN.product_qty) ELSE NULL END as product_qty,
        MAIN.reference as reference,
        MAIN.company_id as company_id
        FROM
        (SELECT
            MIN(sq.id) as id,
            sq.product_id,
            date_trunc('week', to_date(to_char(CURRENT_DATE, 'YYYY/MM/DD'), 'YYYY/MM/DD')) as date,
            sum(sq.quantity) AS product_qty,
            'Starting Inventory' AS reference,
            sq.company_id
            FROM
            stock_quant as sq
            LEFT JOIN
            product_product ON product_product.id = sq.product_id
            LEFT JOIN
            stock_location location_id ON sq.location_id = location_id.id
            WHERE
            location_id.usage = 'internal'
            GROUP BY date, sq.product_id, sq.company_id
            UNION ALL
            SELECT
            MIN(-sm.id) as id,
            sm.product_id,
            CASE WHEN sm.date_expected > CURRENT_DATE
            THEN date_trunc('week', to_date(to_char(sm.date_expected, 'YYYY/MM/DD'), 'YYYY/MM/DD'))
            ELSE date_trunc('week', to_date(to_char(CURRENT_DATE, 'YYYY/MM/DD'), 'YYYY/MM/DD')) END
            AS date,
            sm.product_qty AS product_qty,
            Case WHEN sm.picking_id IS NOT NULL
            THEN sp.name
            ELSE 'Starting Inventory' end as reference,
            sm.company_id
            FROM
               stock_move as sm
            LEFT JOIN
               product_product ON product_product.id = sm.product_id
            LEFT JOIN
            stock_location dest_location ON sm.location_dest_id = dest_location.id
            LEFT JOIN
            stock_location source_location ON sm.location_id = source_location.id
            LEFT JOIN
            stock_picking sp ON sp.id=sm.picking_id
            WHERE
            sm.state IN ('confirmed','assigned','waiting') and
            source_location.usage != 'internal' and dest_location.usage = 'internal'
            GROUP BY sm.date_expected,sm.product_id, sm.company_id, sm.picking_id, sm.product_qty,sp.name
            UNION ALL
            SELECT
                MIN(-sm.id) as id,
                sm.product_id,
                CASE WHEN sm.date_expected > CURRENT_DATE
                    THEN date_trunc('week', to_date(to_char(sm.date_expected, 'YYYY/MM/DD'), 'YYYY/MM/DD'))
                    ELSE date_trunc('week', to_date(to_char(CURRENT_DATE, 'YYYY/MM/DD'), 'YYYY/MM/DD')) END
                AS date,
                SUM(-(sm.product_qty)) AS product_qty,
                sp.name AS reference,
                sm.company_id
            FROM
               stock_move as sm
            LEFT JOIN
               product_product ON product_product.id = sm.product_id
            LEFT JOIN
               stock_location source_location ON sm.location_id = source_location.id
            LEFT JOIN
               stock_location dest_location ON sm.location_dest_id = dest_location.id
            LEFT JOIN
                stock_picking sp ON sp.id=sm.picking_id
            WHERE
                sm.state IN ('confirmed','assigned','waiting') and
            source_location.usage = 'internal' and dest_location.usage != 'internal'
            GROUP BY sm.date_expected,sm.product_id, sm.company_id, sm.picking_id, sp.name)
         as MAIN
     LEFT JOIN
     (SELECT DISTINCT date
      FROM
      (
             SELECT date_trunc('week', CURRENT_DATE) AS DATE
             UNION ALL
             SELECT date_trunc('week', to_date(to_char(sm.date_expected, 'YYYY/MM/DD'), 'YYYY/MM/DD')) AS date
             FROM stock_move sm
             LEFT JOIN
             stock_location source_location ON sm.location_id = source_location.id
             LEFT JOIN
             stock_location dest_location ON sm.location_dest_id = dest_location.id
             WHERE
             sm.state IN ('confirmed','assigned','waiting') and sm.date_expected > CURRENT_DATE and
             ((dest_location.usage = 'internal' AND source_location.usage != 'internal')
              or (source_location.usage = 'internal' AND dest_location.usage != 'internal'))) AS DATE_SEARCH)
             SUB ON (SUB.date IS NOT NULL)
    GROUP BY MAIN.product_id,SUB.date, MAIN.date, MAIN.company_id, MAIN.reference, MAIN.product_qty
    ) AS FINAL WHERE product_qty IS NOT NULL
    GROUP BY product_id,date,id,company_id,reference)""")

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not orderby:
            orderby = 'id, product_id, date'
        return super(ReportStockForecat, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
