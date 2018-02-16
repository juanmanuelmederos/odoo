odoo.define('web_dashboard.dashboard_tests', function (require) {
"use strict";

var DashboardView = require('web_dashboard.DashboardView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            website : {
                fields: [],
                records: [],
            },
        };
    }
}, function () {

    QUnit.module('DashboardView');

    QUnit.test('simple dashboard rendering', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'website',
            data: this.data,
            arch: '<dashboard></dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_dashboard_view').length, 1, "root has a child with 'o_dashboard_view' class");
        
        dashboard.destroy();
    });


    QUnit.only('dashboard with single group', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'website',
            data: this.data,
            debug: 1,
            arch: '<dashboard><group></group></dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_group').length, 1, "there should be a div");


    });

});

});