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
            website : {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                },
                records: [{
                    id: 1,
                    display_name: "Name",
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
            model: 'website',
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
            model: 'website',
            data: this.data,
            arch: '<dashboard><group></group></dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_group').length, 1, "there should be a div");


    });

    QUnit.test('Rendering of a stat button of type object in dashboard view', function (assert) {
        assert.expect(5);

        var dashboard = createView({
            View: DashboardView,
            model: 'website',
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
                    assert.strictEqual(event.data.env.model, "website", "The model should be 'website'");
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
            model: 'website',
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
                    assert.strictEqual(event.data.env.model, "website", "The model should be 'website'");
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
            model: 'website',
            data: this.data,
            arch: '<dashboard>' +
                        '<widget name="test"/>' +                               
                    '</dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_widget').length, 1, "there should be node with widget class");
    });

    QUnit.only('Rendering of a field tag', function (assert) {
        assert.expect(1);

        var dashboard = createView({
            View: DashboardView,
            model: 'website',
            data: this.data,
            debug: 1,
            res_id: 1,
            arch: '<dashboard>' +
                        '<field name="name"/>' +                               
                    '</dashboard>',
        });
        assert.strictEqual(dashboard.$('.o_field_widget').length, 1, "there should be node with field_widget class");
    });


});

});