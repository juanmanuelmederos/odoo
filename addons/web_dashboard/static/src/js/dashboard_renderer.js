odoo.define('web_dashboard.DashboardRenderer', function (require) {
    "use strict";

var AbstractRenderer = require('web.AbstractRenderer');

/**
 * Dashboard Renderer
 *
 */
var DashboardRenderer = AbstractRenderer.extend({
    className: "o_dashboard_view",
    /**
     * @override
     */
    init: function (parent, data) {
        this._super.apply(this, arguments);
        this.data = data;
    },
});

return DashboardRenderer;

});
