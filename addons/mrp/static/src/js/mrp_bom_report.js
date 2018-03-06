odoo.define('mrp.mrp_bom_report', function (require) {
'use strict';

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var MrpBomReport = Widget.extend(ControlPanelMixin, {
    events: {
        'click .o_mrp_bom_unfoldable': '_onClickUnfold',
        'click .o_mrp_bom_foldable': '_onClickFold',
        'click .o_mrp_bom_action': '_onClickAction',
    },
    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.reportContext = action.context.context || {'active_id': action.context.active_id || action.params.active_id};
    },
    willStart: function () {
        var self = this;
        var def = this.getHtml().then(function (html) {
            self.html = html;
        });
        return $.when(this._updateContolPanel(), def);
    },
    getHtml: function () {
        return this._rpc({
            model: 'mrp.bom.report',
            method: 'get_html',
            args: [this.reportContext],
        });
    },
    _reload: function () {
        var self = this;
        this.getHtml().then(function (html) {
            self.$el.html(html);
        });
    },
    start: function () {
        this.$el.html(this.html);
        return this._super.apply(this, arguments);
    },
    do_show: function () {
        this._super.apply(this, arguments);
        this._updateContolPanel();
    },
    _updateContolPanel: function () {
        if (!this.$buttonPrint || !this.$searchQty) {
            this._renderSearch();
        }
        var status = {
            cp_content: {
                $buttons: this.$buttonPrint,
                $searchview_buttons: this.$searchQty
            },
        };
        return this.update_control_panel(status);
    },
    _renderSearch: function () {
        this.$buttonPrint = $(QWeb.render('mrp.button'));
        this.$searchQty = $(QWeb.render('mrp.report_bom_search'));
        this.$buttonPrint.on('click', this._onClickPrint.bind(this));
        this.$searchQty.on('focusout', this._onFocusoutQty.bind(this));
    },
    _onClickPrint: function (ev) {
        var childBomIDs = _.map(this.$el.find('.o_mrp_bom_foldable').closest('tr'), function (el) {
            return $(el).data('id');
        });
        framework.blockUI();
        session.get_file({
            url: '/mrp/pdf/mrp_bom_report/' + this.reportContext['active_id'],
            data: {child_bom_ids: JSON.stringify(childBomIDs)},
            complete: framework.unblockUI,
            error: crash_manager.rpc_error.bind(crash_manager),
        });
    },
    _onFocusoutQty: function (ev) {
        var self = this;
        var qty = $(ev.currentTarget).val().trim();
        if (qty) {
            this.reportContext.searchQty = qty;
            this._reload();
        }
    },
    _removeLines: function ($el) {
        var self = this;
        var activeID = $el.data('id');
        _.each(this.$('tr[parent_id='+ activeID +']'), function (parent) {
            var $parent = self.$(parent);
            var $el = self.$('tr[parent_id='+ $parent.data('id') +']');
            if ($el.length) {
                self._removeLines($parent);
            }
            $parent.remove();
        });
    },
     _onClickUnfold: function (ev) {
        var $parent = $(ev.currentTarget).closest('tr');
        var activeID = $parent.data('id');
        var qty = $parent.data('qty');
        var level = $parent.data('level') || 0;
        this._rpc({
            model: 'mrp.bom.report',
            method: 'get_html',
            args: [this.reportContext, activeID, parseFloat(qty), level + 1],
        })
        .then(function (html) {
            $parent.after(html);
        });
        $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
    },
    _onClickFold: function (ev) {
        this._removeLines($(ev.currentTarget).closest('tr'));
        $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
    },
    _onClickAction: function (ev) {
        return this.do_action({
            type: 'ir.actions.act_window',
            res_model: $(ev.currentTarget).data('model'),
            res_id: $(ev.currentTarget).data('res-id'),
            views: [[false, 'form']],
            target: 'current'
        });
    },
});

core.action_registry.add('mrp_bom_report', MrpBomReport);
return MrpBomReport;

});
