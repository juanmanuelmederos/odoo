odoo.define('payment_wechatpay.qrcode', function (require) {
"use strict";

var payment = require('payment.payment_form');
var rpc = require("web.rpc");
var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var QWeb = core.qweb;
var _t = core._t;

ajax.loadXML("/payment_wechatpay/static/src/xml/qrcode.xml", QWeb);

payment.include({

    payEvent: function (ev) {
        var checked_radio = this.$('input[type="radio"]:checked');
        if (checked_radio[0].dataset.provider == 'wechatpay') {
            this._super.apply(this, arguments);
            ev.target.disabled = true;
            var self = this;
            var $tx_url = this.$('input[name="prepare_tx_url"]');
            var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
            var $loader = '<div class="container text-center text-muted">'+
                            '<i class="fa fa-circle-o-notch fa-4x fa-spin"></i>'+
                        '</div>';
            $($loader).appendTo(self.$el);
            ajax.jsonRpc($tx_url[0].value, 'call', {
                'acquirer_id': parseInt(acquirer_id),
            }).then(function (result) {
                rpc.query({
                    model: 'ir.attachment',
                    method: 'search_read',
                    args: [[['name', '=', 'wechatpay ' + $(result)[0].querySelectorAll('input[name=body]')[0].value]], ['id']],
                    limit: 1,
                })
                .then(function (res_id){
                    var $Img = $('<img/>', {
                        class: 'img img-responsive',
                        src: '/web/image/'+ res_id[0].id +'',
                        style: "margin: auto"
                    });
                    self.$('.container').remove();
                    new Dialog(this, {
                        title: ('WeChat Payment'),
                        buttons: [{text: _t("Close"),classes : "btn-primary close_qrcode", close: true, click: function () {
                        ev.target.disabled = false;
                    }}],
                        $content: QWeb.render('wechatpay.qrcode', {image_id: res_id[0].id}),
                    }).open();
                });
            }).fail(function (message, data) {
                self.displayError(
                    _t('Server Error'),
                    _t("We are not able to redirect you to the payment form.<") +
                       data.data.message
                );
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
