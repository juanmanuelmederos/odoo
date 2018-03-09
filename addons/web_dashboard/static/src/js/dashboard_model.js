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
        var self = this;
        var kpis = dataPoint.fieldsInfo.dashboard;
        var kpisNames = _.map(kpis, function(kpi) {return kpi.name;});
        var def = self._rpc(
            {
                model: dataPoint.model,
                method: 'read_group',
                fields: kpisNames,
                domain: dataPoint.domain,
                groupBy: [],
                orderBy: [],
                lazy: true,
            }).then(function (result) {
                _.each(kpisNames, function(kpiName) {
                    dataPoint.data[kpiName] = result.kpiName;
                });
            });
        return $.when.apply($, def).then(function () {return ;});
    },
});

return DashboardModel;

});
