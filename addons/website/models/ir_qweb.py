# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class QWeb(models.AbstractModel):
    """ QWeb object for rendering stuff in the website context """

    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form': 'action',
        'a': 'href',
    }

    CDN_TRIGGERS = {
        'link':    'href',
        'script':  'src',
        'img':     'src',
    }

    def _post_processing_att(self, tagName, atts, options, values):
        """ Compute the value of an attribute while rendering the template. """
        atts = super(QWeb, self)._post_processing_att(tagName, atts, options, values)
        for name, value in atts.iteritems():
            if request and getattr(request, 'website', None) and request.website.cdn_activated and (name == self.URL_ATTRS.get(tagName) or name == self.CDN_TRIGGERS.get(tagName)):
                atts[name] = request.website.get_cdn_url(value)
        return atts

    def _is_static_node(self, el):
        url_att = self.URL_ATTRS.get(el.tag)
        cdn_att = self.CDN_TRIGGERS.get(el.tag)
        return super(QWeb, self)._is_static_node(el) and \
                (not url_att or not el.get(url_att)) and \
                (not cdn_att or not el.get(cdn_att))
