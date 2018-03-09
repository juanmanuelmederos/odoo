odoo.define('web_dashboard.DashboardModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');

var DashboardModel = BasicModel.extend({

	//--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method should return the complete state necessary for the renderer
     * to display the currently viewed data.
     *
     * @returns {Object}
     */
    load: function (params) {
        params.type = 'record';
        var dataPoint = this._makeDataPoint(params);
        return this._load(dataPoint, params).then(function () {
            return dataPoint.id;
        });
    },
    _load: function (dataPoint) {
        var fields = dataPoint.getFieldNames();
        return this._rpc({
            model: dataPoint.model,
            method: 'read_group',
            fields: fields,
            domain: dataPoint.domain,
            groupBy: [],
            orderBy: [],
            lazy: true,
        }).then(function (result) {
            result = result[0];
            _.each(fields, function (kpiName) {
                dataPoint.data[kpiName] = result[kpiName];
            });
            dataPoint.count = result.__count;
        });
    },
});

return DashboardModel;

});
