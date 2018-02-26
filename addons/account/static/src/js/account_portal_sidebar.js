odoo.define('account.AccountPortalSidebar', function (require) {
"use strict";

require('web.dom_ready');
var core = require('web.core');
var time = require('web.time');

var _t = core._t;

if (!$('.o_portal_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_sidebar'");
}

$("#sidebar_content .o_timeago").each(function (index, el) {
    var dateTime = moment(time.auto_str_to_date($(el).attr('datetime'))),
        today = moment().startOf('day'),
        diff = dateTime.diff(today, 'days', true),
        displayStr;

    if (diff === 0){
        displayStr = _t('Due today');
    } else if (diff > 0) {
        displayStr = _.str.sprintf(_t('Due in %d days'), Math.abs(diff));
    } else {
        displayStr = _.str.sprintf(_t('%d days overdue'), Math.abs(diff));
    }
     $(el).text(displayStr);
});

var $HtmlIframe = $('iframe#invoice_html');
$HtmlIframe.load(function () {
    var $body = $(this).contents().find('body');
    this.style.height = $body.scrollParent().height() + 'px';
    $body.css('width', '100%');
});

$('a#print_invoice_report').on('click', function (ev) {
    ev.preventDefault();
    var url = $(this).attr('href'),
        iFrameJQueryObject = $('<iframe id="print_invoice_pdf" src="'+ url +'" style="display:none"></iframe>'),
        pdfFrame = $('iframe#print_invoice_pdf');
    if (pdfFrame.length) {
        pdfFrame.get(0).contentWindow.print();
    } else {
        $('body').append(iFrameJQueryObject);
        iFrameJQueryObject.on('load', function (){
            $(this).get(0).contentWindow.print();
        });
    }
});
});
