odoo.define('web_dashboard.DashboardView', function (require) {
"use strict";

var DashboardController = require('web_dashboard.DashboardController');
var DashboardModel = require('web_dashboard.DashboardModel');
var DashboardRenderer = require('web_dashboard.DashboardRenderer');
var BasicView = require('web.BasicView');
var core = require('web.core');
var viewRegistry = require('web.view_registry');

var _lt = core._lt;

var DashboardView = BasicView.extend({
    display_name: _lt('Dashboard'),
    icon: 'fa-globe',
    config: {
        Model: DashboardModel,
        Controller: DashboardController,
        Renderer: DashboardRenderer,
    },
});

viewRegistry.add('dashboard', DashboardView);

return DashboardView;

});
