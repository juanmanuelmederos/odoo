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
});

return DashboardRenderer;

});
