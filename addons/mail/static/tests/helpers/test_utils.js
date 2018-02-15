odoo.define('mail.testUtils', function (require) {
"use strict";

var Discuss = require('mail.chat_discuss');

var AbstractService = require('web.AbstractService');
var Bus = require('web.Bus');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

/**
 * Test Utils
 *
 * In this module, we define some utility functions to create mock objects
 * in the mail module, such as the BusService or Discuss.
 */

/**
 * Create a mock bus_service, using 'bus' instead of bus.bus
 *
 * @param {web.bus} bus
 * @return {AbstractService} the mock bus_service
 */
function createBusService(bus) {
    var BusService =  AbstractService.extend({
        name: 'bus_service',
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            if (!bus) {
                bus = new Bus();
            }
            this.bus = new _.extend(bus, {
                /**
                 * Do nothing
                 */
                start_polling: function () {},
            });
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Get the bus
         */
        getBus: function () {
            return this.bus;
        },
    });

    return BusService;
}

/**
 * Create asynchronously a discuss widget.
 * This is async due to chat_manager service that needs to be ready.
 *
 * @param {Object} params
 * @return {$.Promise} resolved with the discuss widget
 */
function createDiscuss(params) {
    var Parent = Widget.extend({
        do_push_state: function () {},
    });
    var parent = new Parent();
    testUtils.addMockEnvironment(parent, _.extend(params, {
        archs: {
            'mail.message,false,search': '<search/>',
        },
    }));
    var discuss = new Discuss(parent, params);
    discuss.set_cp_bus(new Widget());
    var selector = params.debug ? 'body' : '#qunit-fixture';
    discuss.appendTo($(selector));

    return discuss.call('chat_manager', 'isReady').then(function () {
        return discuss;
    });
}

/**
 * In Phantomjs, there is a crash when calling window.getSelection
 * in order for the tests to work, for the specific test that uses it, replace
 * the default window.getSelection by a mock
 * 
 * usage:
 *     QUnit.test('...',function(done){
 *          var original = mailTestUtils.replaceWindowGetSelectionForPhantomJs();
 *          
 *          // do something that needs to use window.getSelection()
 *          assert.strictEqual(....);
 *          
 *          // restore the original function
 *          mailTestUtils.restoreWindowGetSelectionForPhantomJs(original);
 *      
 *          // finish the test
 *          done();
 *     })
 *
 * @returns {function} the original window.getSelection so it can be restored by calling restoreWindowGetSelectionForPhantomJs
 */

function replaceWindowGetSelectionForPhantomJs() {
    var originalGetSelection = window.getSelection;
    window.getSelection = function(){
        return {
            removeAllRanges:function(){

            },
            addRange:function(range){

            },
            getRangeAt:function(index){
                return {
                    startOffset : 0
                };
            },            
            anchorNode:{
                parentNode:{
                    childNodes:[{
                        outerHTML:"blabla",
                        nodeType:3,
                        textContent:'@'
                    }]
                }
            }
        };
    }
    return originalGetSelection;
}

/**
 * after using replaceWindowGetSelectionForPhantomJs, at the end of your test
 * you must restore the default function so there is no impact to the other tests
 * 
 * @param {function} originalFunction 
 */
function restoreWindowGetSelectionForPhantomJs(originalFunction) {
    window.getSelection = originalFunction;

}

return {
    createBusService: createBusService,
    createDiscuss: createDiscuss,
    replaceWindowGetSelectionForPhantomJs:replaceWindowGetSelectionForPhantomJs,
    restoreWindowGetSelectionForPhantomJs:restoreWindowGetSelectionForPhantomJs
};

});
