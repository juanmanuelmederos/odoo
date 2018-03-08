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
        var def = this.getHtml().then(function (result) {
            self.lines = result['lines'];
            self.searchVariants = result['variants'];
            self.bomUomName = result['bom_uom_name'];
            self.bomQty = result['bom_qty'];
        });
        return $.when(def, this._super.apply(this, arguments));
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
        this.getHtml().then(function (result) {
            self.$el.html(result['lines']);
        });
    },
    start: function () {
        this.$el.html(this.lines);
        this._renderSearch();
        this._updateContolPanel();
        return this._super.apply(this, arguments);
    },
    do_show: function () {
        this._super.apply(this, arguments);
        this._updateContolPanel();
    },
    _updateContolPanel: function () {
        var status = {
            cp_content: {
                $buttons: this.$buttonPrint,
                $searchview_buttons: this.$searchView
            },
        };
        return this.update_control_panel(status);
    },
    _renderSearch: function () {
        this.$buttonPrint = $(QWeb.render('mrp.button'));
        this.$buttonPrint.on('click', this._onClickPrint.bind(this));
        this.$searchView = $(QWeb.render('mrp.report_bom_search', {'variants': this.searchVariants, 'bom_uom_name': this.bomUomName, 'bom_qty': this.bomQty}));
        this.$searchView.find('.o_mrp_bom_report_qty').on('focusout', this._onFocusoutQty.bind(this));
        this.$searchView.find('.o_mrp_bom_report_variants').on('click', this._onClickVariants.bind(this));
    },
    _onClickPrint: function (ev) {
        var childBomIDs = _.map(this.$el.find('.o_mrp_bom_foldable').closest('tr'), function (el) {
            return $(el).data('id');
        });
        framework.blockUI();
        var values = {
            child_bom_ids: JSON.stringify(childBomIDs),
            searchQty: this.reportContext.searchQty,
            searchVariant: this.reportContext.searchVariant
        }
        session.get_file({
            url: '/mrp/pdf/mrp_bom_report/' + this.reportContext['active_id'],
            data: values,
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
    _onClickVariants: function (ev) {
        this.reportContext.searchVariant = $(ev.currentTarget).val();
        this._reload();
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
        var lineID = $parent.data('line');
        var qty = $parent.data('qty');
        var level = $parent.data('level') || 0;
        this._rpc({
            model: 'mrp.bom.report',
            method: 'get_html',
            args: [this.reportContext, activeID, parseFloat(qty), lineID, level + 1],
        })
        .then(function (result) {
            $parent.after(result['lines']);
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
