# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestXMLID(TransactionCase):
    def create(self, model, data, mode, noupdate):
        """ Create records with their XMLID. """
        return self.env[model]._create_with_xmlid(data, mode, noupdate)

    def create_xmlid(self, xml_id, record, mode, noupdate):
        """ Create an XMLID for the given record. """
        self.env['ir.model.data']._create_xmlid(xml_id, record, mode, noupdate)

    def get_data(self, xml_id):
        module, suffix = xml_id.split('.')
        domain = [('module', '=', module), ('name', '=', suffix)]
        return self.env['ir.model.data'].search(domain)

    def test_create(self):
        model = 'res.partner.category'
        xml_id = 'test_convert.category_foo'

        # create category
        category = self.create(model, [(xml_id, {'name': 'Foo'})], 'init', False)
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')

        # update category
        category1 = self.create(model, [(xml_id, {'name': 'Bar'})], 'update', False)
        self.assertEqual(category, category1)
        self.assertEqual(category.name, 'Bar')

        # update category
        category2 = self.create(model, [(xml_id, {'name': 'Baz'})], 'update', True)
        self.assertEqual(category, category2)
        self.assertEqual(category.name, 'Baz')

        # check data
        self.assertEqual(self.get_data(xml_id).noupdate, False)

    def test_create_noupdate(self):
        model = 'res.partner.category'
        xml_id = 'test_convert.category_foo'

        # create category
        category = self.create(model, [(xml_id, {'name': 'Foo'})], 'init', True)
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')

        # update category
        category1 = self.create(model, [(xml_id, {'name': 'Bar'})], 'update', False)
        self.assertEqual(category, category1)
        self.assertEqual(category.name, 'Foo')

        # update category
        category2 = self.create(model, [(xml_id, {'name': 'Baz'})], 'update', True)
        self.assertEqual(category, category2)
        self.assertEqual(category.name, 'Foo')

        # check data
        self.assertEqual(self.get_data(xml_id).noupdate, True)

    def test_create_noupdate_multi(self):
        model = 'res.partner.category'
        data = [
            ('test_convert.category_foo', {'name': 'Foo'}),
            ('test_convert.category_bar', {'name': 'Bar'}),
        ]

        # create category
        categories = self.create(model, data, 'init', True)
        foo = self.env.ref('test_convert.category_foo')
        bar = self.env.ref('test_convert.category_bar')
        self.assertEqual(categories, foo + bar)
        self.assertEqual(foo.name, 'Foo')
        self.assertEqual(bar.name, 'Bar')

        # check data
        self.assertEqual(self.get_data('test_convert.category_foo').noupdate, True)
        self.assertEqual(self.get_data('test_convert.category_bar').noupdate, True)

    def test_create_order(self):
        model = 'res.partner.category'

        # create categories
        foo = self.create(model, [('test_convert.category_foo', {'name': 'Foo'})], 'init', False)
        bar = self.create(model, [('test_convert.category_bar', {'name': 'Bar'})], 'init', True)
        baz = self.create(model, [('test_convert.category_baz', {'name': 'Baz'})], 'init', False)
        self.assertEqual(foo.name, 'Foo')
        self.assertEqual(bar.name, 'Bar')
        self.assertEqual(baz.name, 'Baz')

        # update them, and check the order or result
        data = [
            ('test_convert.category_foo', {'name': 'FooX'}),
            ('test_convert.category_bar', {'name': 'BarX'}),
            ('test_convert.category_baz', {'name': 'BazX'}),
        ]
        cats = self.create(model, data, 'update', False)
        self.assertEqual(list(cats), [foo, bar, baz])
        self.assertEqual(foo.name, 'FooX')
        self.assertEqual(bar.name, 'Bar')
        self.assertEqual(baz.name, 'BazX')

    def test_create_inherits(self):
        model = 'res.users'
        xml_id = 'test_convert.user_foo'
        par_xml_id = xml_id + '_res_partner'

        # create user
        user = self.create(model, [(xml_id, {'name': 'Foo', 'login': 'foo'})], 'init', False)
        self.assertEqual(user, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(user.partner_id, self.env.ref(par_xml_id, raise_if_not_found=False))
        self.assertEqual(user.name, 'Foo')
        self.assertEqual(user.login, 'foo')

    def test_recreate(self):
        model = 'res.partner.category'
        xml_id = 'test_convert.category_foo'

        # create category
        category = self.create(model, [(xml_id, {'name': 'Foo'})], 'init', False)
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')

        # suppress category
        category.unlink()
        self.assertFalse(self.env.ref(xml_id, raise_if_not_found=False))

        # update category, this should recreate it
        category = self.create(model, [(xml_id, {'name': 'Foo'})], 'update', False)
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')

    def test_create_xmlid(self):
        model = 'res.users'
        xml_id = 'test_convert.user_foo'
        par_xml_id = xml_id + '_res_partner'

        # create user
        user = self.env[model].create({'name': 'Foo', 'login': 'foo'})

        # assign it an xml_id
        self.create_xmlid(xml_id, user, 'init', True)
        self.assertEqual(user, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(user.partner_id, self.env.ref(par_xml_id, raise_if_not_found=False))
        self.assertEqual(self.get_data(xml_id).noupdate, True)
