odoo.define('web_dashboard.DashboardRenderer', function (require) {
    "use strict";

var FormRenderer = require('web.FormRenderer');

/**
 * Dashboard Renderer
 *
 */
var DashboardRenderer = FormRenderer.extend({
    className: "o_dashboard_view o_form_view",

    _registerModifiers: function() {
    	return {};
    },

    /**
     * Override _renderFieldWidget of BasicRenderer
     *
     * @private
     * @param {Object} node
     * @param {Object} record
     * @param {Object} [options] passed to @_registerModifiers
     * @param {string} [options.mode] either 'edit' or 'readonly' (defaults to
     *   this.mode, the mode of the renderer)
     * @returns {jQueryElement}
     */
    _renderFieldWidget: function (node, record, options) {
        options = options || {};
        var fieldName = node.attrs.name;
        // Register the node-associated modifiers
        var mode = options.mode || this.mode;
        // Initialize and register the widget
        // Readonly status is known as the modifiers have just been registered
        var Widget = record.fieldsInfo[this.viewType][fieldName].Widget;
        var widget = new Widget(this, fieldName, record, {
            mode: mode,
            viewType: this.viewType,
        });

        // Register the widget so that it can easily be found again
        if (this.allFieldWidgets[record.id] === undefined) {
            this.allFieldWidgets[record.id] = [];
        }
        this.allFieldWidgets[record.id].push(widget);

        widget.__node = node; // TODO get rid of this if possible one day

        // Prepare widget rendering and save the related deferred
        var def = widget._widgetRenderAndInsert(function () {});
        var async = def.state() === 'pending';
        var $el = async ? $('<div>') : widget.$el;
        if (async) {
            this.defs.push(def);
        }

        // Update the modifiers registration by associating the widget and by
        // giving the modifiers options now (as the potential callback is
        // associated to new widget)
        var self = this;
        def.then(function () {
            if (async) {
                $el.replaceWith(widget.$el);
            }
            self._postProcessField(widget, node);
        });

        return $el;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroup: function (node) {
        var self = this;
        var $result = $('<table/>', {class: 'o_group o_inner_group'});

        var col = parseInt(node.attrs.col, 10) || 2;

        if (node.attrs.string) {
            var $sep = $('<tr><td colspan="' + col + '" style="width: 100%;"><div class="o_horizontal_separator o_dashboard_group_title">' + node.attrs.string + '</div></td></tr>');
            $result.append($sep);
        }

        var rows = [];
        var $firstCurrentRow = $('<tr/>');
        var $secondCurrentRow = $('<tr/>');
        var currentColspan = 0;
        _.each(node.children, function (child) {
            if (child.tag === 'newline') {
                rows.push($firstCurrentRow,$secondCurrentRow);
                $firstCurrentRow = $('<tr/>');
                $secondCurrentRow = $('<tr/>');
                currentColspan = 0;
                return;
            }

            currentColspan ++;

            if (currentColspan > col) {
                rows.push($firstCurrentRow,$secondCurrentRow);
                $firstCurrentRow = $('<tr/>');
                $secondCurrentRow = $('<tr/>');
                currentColspan = 1;
            }
            var $tds = self._renderInnerGroupField(child);
            $firstCurrentRow.append($tds.label);
            $secondCurrentRow.append($tds.value);
        });
        rows.push($firstCurrentRow,$secondCurrentRow);

        _.each(rows, function ($tr) {
            var ColSize = 100 / col;
            _.each($tr.children(), function (el) {
                var $el = $(el);
                $el.css('width', ((parseInt($el.attr('colspan'), 10) || 1) * ColSize) + '%');
            });
            $result.append($tr);
        });

        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroupField: function (node) {
        var $el = this._renderFieldWidget(node, this.state);
        var $value = $('<td/>').append($el);
        var $label = this._renderInnerGroupLabel(node);
        return  {label: $label, value: $value};
    },
    /**
     * @private
     * @param {string} label
     * @returns {jQueryElement}
     */
    _renderInnerGroupLabel: function (label) {
        return $('<td/>', {class: 'o_td_label'})
            .append(this._renderTagLabel(label));
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagGroup: function (node) {
        var self = this;
        var isOuterGroup = _.some(node.children, function (child) {
            return child.tag === 'group';
        });
        if (!isOuterGroup) {
            return this._renderInnerGroup(node);
        }

        var $result = $('<div/>', {class: 'o_group'});
        var colSize = Math.max(1, Math.round(12 / (parseInt(node.attrs.col, 10) || 2)));
        $result.append(_.map(node.children, function (child) {
            if (child.tag === 'newline') {
                return $('<br/>');
            }
            var $child = self._renderNode(child);
            $child.addClass('o_group_col_' + (colSize * (parseInt(child.attrs.colspan, 10) || 1)));
            return $child;
        }));
        this._handleAttributes($result, node);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagLabel: function (node) {
        var self = this;
        var text;
        var fieldName = node.tag === 'label' ? node.attrs.for : node.attrs.name;
        if ('string' in node.attrs) { // allow empty string
            text = node.attrs.string;
        } else if (fieldName) {
            text = this.state.fields[fieldName].string;
        } else  {
            return this._renderGenericTag(node);
        }
        var $result = $('<label>', {
            class: 'o_form_label',
            for: this._getIDForLabel(fieldName),
            text: text,
        });
        if (node.tag === 'label') {
            this._handleAttributes($result, node);
        }
        return $result;
    },
});

return DashboardRenderer;

});
