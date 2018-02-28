odoo.define('web.sortable.extensions', function () {
'use strict';

/**
 * The RubaXa sortable library extensions and fixes should be done here to
 * avoid patching in place.
 */

var proto = Sortable.prototype;
var onTouchMove = proto._onTouchMove;

$.extend(proto, {
	// extend _onTouchMove to add additional css property on element
	_onTouchMove: function (/**TouchEvent*/evt) {
		onTouchMove.call(this,evt);
		var clonedDiv = $(this.el).find('.o_kanban_record_clone');
		clonedDiv.css('transform', clonedDiv.css('transform') + ' rotate(-3deg)');
	},
});
});
