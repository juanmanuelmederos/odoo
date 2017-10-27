# -*- coding: utf-8 -*-

from contextlib import contextmanager
from email.utils import formataddr

from odoo import api
from odoo.tests import common


class BaseFunctionalTest(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls._quick_create_ctx = {
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }

        user_group_employee = cls.env.ref('base.group_user')
        cls.user_employee = cls.env['res.users'].with_context(cls._quick_create_ctx).create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_employee.id])]})
        cls.user_admin = cls.env.user

        cls.channel_listen = cls.env['mail.channel'].with_context(cls._quick_create_ctx).create({'name': 'Listener'})

        cls.test_record = cls.env['mail.test.simple'].with_context(cls._quick_create_ctx).create({'name': 'Test'})

    @contextmanager
    def sudoAs(self, login):
        old_uid = self.uid
        try:
            user = self.env['res.users'].sudo().search([('login', '=', login)])
            # switch user
            self.uid = user.id
            self.env = self.env(user=self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)


class MockEmails(common.SingleTransactionCase):

    def setUp(self):
        super(MockEmails, self).setUp()
        self._mails_args[:] = []
        self._mails[:] = []

    @classmethod
    def setUpClass(cls):
        super(MockEmails, cls).setUpClass()
        cls._mails_args = []
        cls._mails = []

        def build_email(self, *args, **kwargs):
            cls._mails_args.append(args)
            cls._mails.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        @api.model
        def send_email(self, message, *args, **kwargs):
            return message['Message-Id']

        cls.env['ir.mail_server']._patch_method('build_email', build_email)
        cls.env['ir.mail_server']._patch_method('send_email', send_email)

    def assertEmails(self, partner_from, recipients, **values):
        """ Tools method to ease the check of send emails """
        expected_email_values = []
        for partners in recipients:
            expected = {
                'email_from': formataddr((partner_from.name, partner_from.email)),
                'email_to': [formataddr((partner.name, partner.email)) for partner in partners]
            }
            if 'reply_to' in values:
                expected['reply_to'] = values['reply_to']
            if 'subject' in values:
                expected['subject'] = values['subject']
            if 'body' in values:
                expected['body'] = values['body']
            if 'body_content' in values:
                expected['body_content'] = values['body_content']
            if 'body_alt_content' in values:
                expected['body_alternative_content'] = values['body_alt_content']
            if 'references' in values:
                expected['references'] = values['references']
            if 'ref_content' in values:
                expected['references_content'] = values['ref_content']
            expected_email_values.append(expected)

        self.assertEqual(len(self._mails), len(expected_email_values))
        for expected in expected_email_values:
            sent_mail = next((mail for mail in self._mails if set(mail['email_to']) == set(expected['email_to'])), False)
            self.assertTrue(bool(sent_mail), 'Expected mail to %s not found' % expected['email_to'])
            for val in ['email_from', 'reply_to', 'subject', 'body', 'references']:
                if val in expected:
                    self.assertEqual(expected[val], sent_mail[val], 'Value for %s: expected %s, received %s' % (val, expected[val], sent_mail[val]))
            for val in ['body_content', 'body_alternative', 'references_content']:
                if val in expected:
                    self.assertIn(expected[val], sent_mail[val[:-8]], 'Value for %s: %s does not contain %s' % (val, sent_mail[val[:-8]], expected[val]))

    @classmethod
    def tearDownClass(cls):
        # Remove mocks
        cls.env['ir.mail_server']._revert_method('build_email')
        cls.env['ir.mail_server']._revert_method('send_email')
        super(MockEmails, cls).tearDownClass()

    def _init_mock_build_email(self):
        self._mails_args[:] = []
        self._mails[:] = []

    def format(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
               extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
               cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
        return template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)

    def format_and_process(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
                           extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                           cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                           model=None, target_model='mail.test.simple', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        mail = self.format(template, to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])


class TestMail(BaseFunctionalTest, MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMail, cls).setUpClass()

        user_group_portal = cls.env.ref('base.group_portal')
        user_group_public = cls.env.ref('base.group_public')

        cls.partner_1 = cls.env['res.partner'].with_context(cls._quick_create_ctx).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})
        cls.partner_2 = cls.env['res.partner'].with_context(cls._quick_create_ctx).create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com'})

        Users = cls.env['res.users'].with_context(cls._quick_create_ctx)
        cls.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_public.id])]})
        cls.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'signature': 'SignChell',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_portal.id])]})

        TestModel = cls.env['mail.test'].with_context(cls._quick_create_ctx)
        cls.test_pigs = TestModel.create({
            'name': 'Pigs',
            'description': 'Fans of Pigs, unite !',
            'alias_name': 'pigs',
            'alias_contact': 'followers',
        })
        cls.test_public = TestModel.create({
            'name': 'Public',
            'description': 'NotFalse',
            'alias_name': 'public',
            'alias_contact': 'everyone'
        })

        cls.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', 'in', (cls.test_public | cls.test_pigs).ids)]).unlink()
