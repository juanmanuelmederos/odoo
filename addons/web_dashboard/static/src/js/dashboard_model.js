odoo.define('web_dashboard.DashboardModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

var DashboardModel = AbstractModel.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.data = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return this.data;
    },
});

return DashboardModel;

});
