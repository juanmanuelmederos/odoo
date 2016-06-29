# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
import datetime

from odoo import api, exceptions, fields, models, _


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource': 'resource_id'}
    _order = "sequence, id"

    note = fields.Text(
        'Description',
        help="Description of the Work Center.")
    capacity = fields.Float(
        'Capacity', default=1.0, oldname='capacity_per_cycle',
        help="Number of pieces that can be produced in parallel.")
    sequence = fields.Integer(
        'Sequence', default=1, required=True,
        help="Gives the sequence order when displaying a list of work centers.")
    color = fields.Integer('Color')
    time_start = fields.Float('Time before prod.', help="Time in minutes for the setup.")
    time_stop = fields.Float('Time after prod.', help="Time in minutes for the cleaning.")
    resource_id = fields.Many2one('resource.resource', 'Resource', ondelete='cascade', required=True)
    routing_line_ids = fields.One2many('mrp.routing.workcenter', 'workcenter_id', "Routing Lines")

    order_ids = fields.One2many('mrp.workorder', 'workcenter_id', "Orders")
    workorder_count = fields.Integer('# Work Orders', compute='_compute_workorder_count')
    workorder_ready_count = fields.Integer('# Read Work Orders', compute='_compute_workorder_ready_count')
    workorder_progress_count = fields.Integer('Total Running Orders', compute='_compute_workorder_progress_count')
    workorder_pending_count = fields.Integer('Total Running Orders', compute='_compute_workorder_pending_count')

    time_ids = fields.One2many('mrp.workcenter.productivity', 'workcenter_id', 'Time Logs')
    working_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Blocked'),
        ('done', 'In Progress')], 'Status', compute="_compute_working_state", store=True)
    blocked_time = fields.Float(
        'Blocked Time', compute='_compute_blocked_time',
        help='Blocked hours over the last month')
    productive_time = fields.Float(
        'Productive Time', compute='_compute_productive_time',
        help='Productive hours over the last month')
    oee = fields.Float(compute='_compute_oee', help='Overall Equipment Efficiency, based on the last month')
    oee_target = fields.Float(string='OEE Target', help="OEE Target in percentage", default=90)
    performance = fields.Integer('Performance', compute='_compute_performance', help='Performance over the last month')

    @api.depends('order_ids.workcenter_id', 'order_ids.state')
    def _compute_workorder_count(self):
        data = self.env['mrp.workorder'].read_group([('workcenter_id', 'in', self.ids), ('state', 'not in', ('done', 'cancel'))], ['workcenter_id'], ['workcenter_id'])
        count_data = dict((item['workcenter_id'][0], item['workcenter_id_count']) for item in data)
        for workcenter in self:
            workcenter.workorder_count = count_data.get(workcenter.id, 0)

    @api.depends('order_ids.workcenter_id', 'order_ids.state')
    def _compute_workorder_ready_count(self):
        data = self.env['mrp.workorder'].read_group([('workcenter_id', 'in', self.ids), ('state', '=', 'ready')], ['workcenter_id'], ['workcenter_id'])
        count_data = dict((item['workcenter_id'][0], item['workcenter_id_count']) for item in data)
        for workcenter in self:
            workcenter.workorder_ready_count = count_data.get(workcenter.id, 0)

    @api.depends('order_ids.workcenter_id', 'order_ids.state')
    def _compute_workorder_progress_count(self):
        data = self.env['mrp.workorder'].read_group([('workcenter_id', 'in', self.ids), ('state', '=', 'progress')], ['workcenter_id'], ['workcenter_id'])
        count_data = dict((item['workcenter_id'][0], item['workcenter_id_count']) for item in data)
        for workcenter in self:
            workcenter.workorder_progress_count = count_data.get(workcenter.id, 0)

    @api.depends('order_ids.workcenter_id', 'order_ids.state')
    def _compute_workorder_pending_count(self):
        data = self.env['mrp.workorder'].read_group([('workcenter_id', 'in', self.ids), ('state', '=', 'pending')], ['workcenter_id'], ['workcenter_id'])
        count_data = dict((item['workcenter_id'][0], item['workcenter_id_count']) for item in data)
        for workcenter in self:
            workcenter.workorder_pending_count = count_data.get(workcenter.id, 0)

    @api.multi
    @api.depends('time_ids.date_end', 'time_ids.loss_type')
    def _compute_working_state(self):
        for workcenter in self:
            time_log = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', workcenter.id)], limit=1)
            if not time_log or time_log.date_end:
                workcenter.working_state = 'normal'
            elif time_log.loss_type in ('productive', 'performance'):
                workcenter.working_state = 'done'
            else:
                workcenter.working_state = 'blocked'

    @api.multi
    def _compute_blocked_time(self):
        # TDE FIXME: productivity loss type should be only losses, probably count other time logs differently ??
        data = self.env['mrp.workcenter.productivity'].read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('date_end', '!=', False),
            ('loss_type', '!=', 'productive')],
            ['duration', 'workcenter_id'], ['workcenter_id'], lazy=False)
        count_data = dict((item['workcenter_id'][0], item['duration']) for item in data)
        for workcenter in self:
            workcenter.blocked_time = count_data.get(workcenter.id, 0.0)

    @api.multi
    def _compute_productive_time(self):
        # TDE FIXME: productivity loss type should be only losses, probably count other time logs differently
        data = self.env['mrp.workcenter.productivity'].read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('date_end', '!=', False),
            ('loss_type', '=', 'productive')],
            ['duration', 'workcenter_id'], ['workcenter_id'], lazy=False)
        count_data = dict((item['workcenter_id'][0], item['duration']) for item in data)
        for workcenter in self:
            workcenter.productive_time = count_data.get(workcenter.id, 0.0)

    @api.depends('blocked_time', 'productive_time')
    @api.one
    def _compute_oee(self):
        if self.productive_time:
            self.oee = round(self.productive_time * 100.0 / (self.productive_time + self.blocked_time), 2)
        else:
            self.oee = 0.0

    @api.multi
    def _compute_performance(self):
        wo_data = self.env['mrp.workorder'].read_group([
            ('date_start', '>=', fields.Datetime.to_string(datetime.datetime.now() - relativedelta.relativedelta(months=1))),
            ('workcenter_id', 'in', self.ids),
            ('state', '=', 'done')], ['duration_expected', 'workcenter_id', 'duration'], ['workcenter_id'], lazy=False)
        duration_expected = dict((data['workcenter_id'][0], data['duration_expected']) for data in wo_data)
        duration = dict((data['workcenter_id'][0], data['duration']) for data in wo_data)
        for workcenter in self:
            if duration.get(workcenter.id):
                workcenter.performance = 100 * duration_expected.get(workcenter.id, 0.0) / duration[workcenter.id]
            else:
                workcenter.performance = 0.0

    @api.multi
    @api.constrains('capacity')
    def _check_capacity(self):
        if any(workcenter.capacity <= 0.0 for workcenter in self):
            raise exceptions.UserError(_('The capacity must be strictly positive.'))

    @api.multi
    def unblock(self):
        self.ensure_one()
        if self.working_state != 'blocked':
            raise exceptions.UserError(_("It has been unblocked already. "))
        times = self.env['mrp.workcenter.productivity'].search([('workcenter_id', '=', self.id), ('date_end', '=', False)])
        times.write({'date_end': fields.Datetime.now()})
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class MrpWorkcenterProductivityLoss(models.Model):
    _name = "mrp.workcenter.productivity.loss"
    _description = "TPM Big Losses"
    _order = "sequence, id"

    name = fields.Char('Reason', required=True)
    sequence = fields.Integer('Sequence', default=1)
    manual = fields.Boolean('Is a Blocking Reason', default=True)
    loss_type = fields.Selection([
        ('availability', 'Availability'),
        ('performance', 'Performance'),
        ('quality', 'Quality'),
        ('productive', 'Productive')], "Effectiveness Category",
        default='availability', required=True)


class MrpWorkcenterProductivity(models.Model):
    _name = "mrp.workcenter.productivity"
    _description = "Workcenter Productivity Log"
    _order = "id desc"
    _rec_name = "loss_id"

    workcenter_id = fields.Many2one('mrp.workcenter', "Work Center", required=True)
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    user_id = fields.Many2one(
        'res.users', "User",
        default=lambda self: self.env.uid)
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason",
        required=True)
    loss_type = fields.Selection(
        "Effectiveness", related='loss_id.loss_type', store=True)
    description = fields.Text('Description')
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now(), required=True)
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_end:
                diff = fields.Datetime.from_string(blocktime.date_end) - fields.Datetime.from_string(blocktime.date_start)
                blocktime.duration = round(diff.total_seconds() / 60.0, 2)
            else:
                blocktime.duration = 0.0

    @api.multi
    def button_block(self):
        self.ensure_one()
        self.workcenter_id.order_ids.end_all()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
