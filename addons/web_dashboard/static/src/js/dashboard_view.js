odoo.define('web_dashboard.DashboardView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var DashboardController = require('web_dashboard.DashboardController');
var DashboardModel = require('web_dashboard.DashboardModel');
var DashboardRenderer = require('web_dashboard.DashboardRenderer');
var viewRegistry = require('web.view_registry');

var _lt = core._lt;

var DashboardView = BasicView.extend({
    display_name: _lt('Dashboard'),
    icon: 'fa-globe', // to change
    config: {
        Model: DashboardModel,
        Controller: DashboardController,
        Renderer: DashboardRenderer,
    },
    groupable: false,
    viewType: 'dashboard',
});

viewRegistry.add('dashboard', DashboardView);

return DashboardView;

});
