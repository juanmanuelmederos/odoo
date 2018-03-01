odoo.define('web_dashboard.DashboardController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var BasicController = require('web.BasicController');

var DashboardController = AbstractController.extend({
	custom_events: _.extend({}, BasicController.prototype.custom_events, {
	        button_clicked: '_onButtonClicked',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When the user clicks on a 'action button', this function determines what
     * should happen.
     *
     * @private
     * @param {Object} attrs the attrs of the button clicked
     * @returns {Deferred}
     */
    _callButtonAction: function (attrs) {
        var self = this;
        var def = $.Deferred();
        var reload = function () {
            return self.isDestroyed() ? $.when() : self.reload();
        };
        this.trigger_up('execute_action', {
            action_data: _.extend({}, attrs, {
                context: attrs.context || {},
            }),
            env: {
            	model: this.modelName,
            },
            on_success: def.resolve.bind(def),
            on_fail: function () {
                reload().always(def.reject.bind(def));
            },
        });
        return this.alive(def);
    },
    /**
     * Disable buttons in the renderer.
     *
     * @override
     * @private
     */
    _disableButtons: function () {
	    this._super.apply(this, arguments);
        this.renderer.disableButtons();
    },
        /**
     * Enable buttons in the renderer.
     *
     * @override
     * @private
     */
    _enableButtons: function () {
        this._super.apply(this, arguments);
        this.renderer.enableButtons();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onButtonClicked: function (event) {
        // stop the event's propagation just in case a dashboard controller have other
        // controllers in its ascendants
        this._disableButtons();
        event.stopPropagation();
        var def = this._callButtonAction(event.data.attrs);
	    def.always(this._enableButtons.bind(this));
    },

});

return DashboardController;

});
