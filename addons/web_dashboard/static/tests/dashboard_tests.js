odoo.define('web_dashboard.dashboard_tests', function (require) {
"use strict";

var DashboardView = require('web_dashboard.DashboardView');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            sale_report : {
                fields: {
                    sold: {string: "Sold", type: "float"},
                    untaxed_total: {string: "untaxed_total", type: "float"}
                },
                records: [{
                    id: 1,
                    sold: 5,
                    untaxed_total: 10,
                },{
                    id: 2,
                    sold: 3,
                    untaxed_total: 20,
                }],
            },
        };
    }
}, function () {

    QUnit.module('DashboardView');

    QUnit.test('simple dashboard rendering', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            arch: '<dashboard></dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_dashboard_view').length, 1, "root has a child with 'o_dashboard_view' class");
        
        dashboard.destroy();
    });


    QUnit.test('dashboard with single group', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            arch: '<dashboard><group></group></dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_group').length, 1, "there should be a div");


    });

    QUnit.test('Rendering of a stat button of type object in dashboard view', function (assert) {
        assert.expect(5);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            arch: '<dashboard>' + 
                        '<div class="oe_button_box" name="button_box">' +
                            '<button name="method" string="Method" type="object" class="oe_stat_button">' +
                            '</button>' +
                        '</div>' +
                    '</dashboard>',
            intercepts: {
                execute_action: function (event) {
                    assert.ok(event, "An execute_action should have been intercepted");
                    assert.strictEqual(event.data.env.model, "sale_report", "The model should be 'sale_report'");
                    assert.strictEqual(event.data.action_data.type, "object", "The type of action should be 'object'");
                }
            },
        });
        assert.strictEqual(dashboard.$('.oe_button_box').length, 1, "there should be a button box");
        assert.strictEqual(dashboard.$('.oe_stat_button').children().length, 1, "there should be exactly one stat button");
        dashboard.$('.oe_stat_button').click();
    });

    QUnit.test('Rendering of a stat button of type action in dashboard view', function (assert) {
        assert.expect(5);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            arch: '<dashboard>' + 
                        '<div class="oe_button_box" name="button_box">' +
                            '<button name="%(action)d" string="Action" type="action" class="oe_stat_button">' +
                            '</button>' +
                        '</div>' +
                    '</dashboard>',
            intercepts: {
                execute_action: function (event) {
                    assert.ok(event, "An execute_action should have been intercepted");
                    assert.strictEqual(event.data.env.model, "sale_report", "The model should be 'sale_report'");
                    assert.strictEqual(event.data.action_data.type, "action", "The type of action should be 'action'");
                }
            },
        });
        assert.strictEqual(dashboard.$('.oe_button_box').length, 1, "there should be a button box");
        assert.strictEqual(dashboard.$('.oe_stat_button').children().length, 1, "there should be exactly one stat button");
        dashboard.$('.oe_stat_button').click();
    });

    QUnit.test('Rendering of a widget tag', function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
            },
            start: function () {
                this.$el.text(JSON.stringify(this.data));
            },
        });
        widgetRegistry.add('test', MyWidget);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<widget name="test"/>' +                               
                    '</dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_widget').length, 1, "there should be a node with widget class");
    });

    QUnit.test('Rendering of a field tag', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            arch: '<dashboard>' +
                        '<field name="sold"/>' +                               
                    '</dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_field_widget').length, 1, "there should be a node with field_widget class");
    });

    QUnit.test('Rendering of a inner group field tag', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'sale_report',
            data: this.data,
            // debug: 1,
            arch: '<dashboard>' +
                        '<group string="At a glance">' +
                            '<field name="sold" widget="float_time"/>' +
                        '</group>' +
                    '</dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_field_widget').length, 1, "there should be a node with field_widget class");
    });


});

});