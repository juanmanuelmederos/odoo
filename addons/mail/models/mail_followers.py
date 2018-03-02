# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import api, fields, models


class Followers(models.Model):
    """ mail_followers holds the data related to the follow mechanism inside
    Odoo. Partners can choose to follow documents (records) of any kind
    that inherits from mail.thread. Following documents allow to receive
    notifications for new messages. A subscription is characterized by:

    :param: res_model: model of the followed objects
    :param: res_id: ID of resource (may be 0 for every objects)
    """
    _name = 'mail.followers'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Document Followers'

    # Note. There is no integrity check on model names for performance reasons.
    # However, followers of unlinked models are deleted by models themselves
    # (see 'ir.model' inheritance).
    res_model = fields.Char(
        'Related Document Model Name', required=True, index=True)
    res_id = fields.Integer(
        'Related Document ID', index=True, help='Id of the followed resource')
    partner_id = fields.Many2one(
        'res.partner', string='Related Partner', ondelete='cascade', index=True)
    channel_id = fields.Many2one(
        'mail.channel', string='Listener', ondelete='cascade', index=True)
    subtype_ids = fields.Many2many(
        'mail.message.subtype', string='Subtype',
        help="Message subtypes followed, meaning subtypes that will be pushed onto the user's Wall.")

    @api.model
    def _add_follower_command(self, res_model, res_ids, partner_data, channel_data, force=True):
        """ Please upate me
        :param force: if True, delete existing followers before creating new one
                      using the subtypes given in the parameters
        """
        force_mode = force or (all(partner_data.values()) and all(channel_data.values()))
        generic = []
        specific = {}
        existing = {}  # {res_id: follower_ids}
        p_exist = {}  # {partner_id: res_ids}
        c_exist = {}  # {channel_id: res_ids}

        followers = self.sudo().search([
            '&',
            '&', ('res_model', '=', res_model), ('res_id', 'in', res_ids),
            '|', ('partner_id', 'in', list(partner_data)), ('channel_id', 'in', list(channel_data))])

        if force_mode:
            followers.unlink()
        else:
            for follower in followers:
                existing.setdefault(follower.res_id, list()).append(follower)
                if follower.partner_id:
                    p_exist.setdefault(follower.partner_id.id, list()).append(follower.res_id)
                if follower.channel_id:
                    c_exist.setdefault(follower.channel_id.id, list()).append(follower.res_id)

        default_subtypes, _internal_subtypes, external_subtypes = \
            self.env['mail.message.subtype'].default_subtypes(res_model)

        if force_mode:
            employee_pids = self.env['res.users'].sudo().search([('partner_id', 'in', list(partner_data)), ('share', '=', False)]).mapped('partner_id').ids
            for pid, data in partner_data.items():
                if not data:
                    if pid not in employee_pids:
                        partner_data[pid] = external_subtypes.ids
                    else:
                        partner_data[pid] = default_subtypes.ids
            for cid, data in channel_data.items():
                if not data:
                    channel_data[cid] = default_subtypes.ids

        # create new followers, batch ok
        gen_new_pids = [pid for pid in partner_data if pid not in p_exist]
        gen_new_cids = [cid for cid in channel_data if cid not in c_exist]
        for pid in gen_new_pids:
            generic.append([0, 0, {'res_model': res_model, 'partner_id': pid, 'subtype_ids': [(6, 0, partner_data.get(pid) or default_subtypes.ids)]}])
        for cid in gen_new_cids:
            generic.append([0, 0, {'res_model': res_model, 'channel_id': cid, 'subtype_ids': [(6, 0, channel_data.get(cid) or default_subtypes.ids)]}])

        # create new followers, each document at a time because of existing followers to avoid erasing
        if not force_mode:
            for res_id in res_ids:
                command = []
                doc_followers = existing.get(res_id, list())

                new_pids = set(partner_data) - set([sub.partner_id.id for sub in doc_followers if sub.partner_id]) - set(gen_new_pids)
                new_cids = set(channel_data) - set([sub.channel_id.id for sub in doc_followers if sub.channel_id]) - set(gen_new_cids)

                # subscribe new followers
                for new_pid in new_pids:
                    command.append((0, 0, {
                        'res_model': res_model,
                        'partner_id': new_pid,
                        'subtype_ids': [(6, 0, partner_data.get(new_pid) or default_subtypes.ids)],
                    }))
                for new_cid in new_cids:
                    command.append((0, 0, {
                        'res_model': res_model,
                        'channel_id': new_cid,
                        'subtype_ids': [(6, 0, channel_data.get(new_cid) or default_subtypes.ids)],
                    }))
                if command:
                    specific[res_id] = command
        return generic, specific

    #
    # Modifying followers change access rights to individual documents. As the
    # cache may contain accessible/inaccessible data, one has to refresh it.
    #
    @api.multi
    def _invalidate_documents(self):
        """ Invalidate the cache of the documents followed by ``self``. """
        for record in self:
            if record.res_id:
                self.env[record.res_model].invalidate_cache(ids=[record.res_id])

    @api.model
    def create(self, vals):
        res = super(Followers, self).create(vals)
        res._invalidate_documents()
        return res

    @api.multi
    def write(self, vals):
        if 'res_model' in vals or 'res_id' in vals:
            self._invalidate_documents()
        res = super(Followers, self).write(vals)
        self._invalidate_documents()
        return res

    @api.multi
    def unlink(self):
        self._invalidate_documents()
        return super(Followers, self).unlink()

    _sql_constraints = [
        ('mail_followers_res_partner_res_model_id_uniq', 'unique(res_model,res_id,partner_id)', 'Error, a partner cannot follow twice the same object.'),
        ('mail_followers_res_channel_res_model_id_uniq', 'unique(res_model,res_id,channel_id)', 'Error, a channel cannot follow twice the same object.'),
        ('partner_xor_channel', 'CHECK((partner_id IS NULL) != (channel_id IS NULL))', 'Error: A follower must be either a partner or a channel (but not both).')
    ]

    # --------------------------------------------------
    # Private tools methods to fetch followers data
    # --------------------------------------------------

    def _get_followers_data(self, res_model, res_ids, pids, cids):
        where_params = (res_model, res_ids, pids, cids)
        query = """
SELECT fol.id, fol.res_id, fol.partner_id, fol.channel_id, array_agg(subtype.id)
FROM mail_followers fol
LEFT JOIN mail_followers_mail_message_subtype_rel fol_rel ON fol_rel.mail_followers_id = fol.id
LEFT JOIN mail_message_subtype subtype ON subtype.id = fol_rel.mail_message_subtype_id
WHERE fol.res_model = %s AND fol.res_id = ANY(%s) AND
    (fol.partner_id = ANY(%s) OR fol.channel_id = ANY(%s))
GROUP BY fol.id"""
        self.env.cr.execute(query, where_params)
        return self.env.cr.fetchall()

    def _get_doc_follower_data(self, doc_data):
        """ Private method allowing to fetch follower data from a given set of
        res_model / res_ids. It returns data for each follower: its follower ID,
        the partner ID (if any), if the partner is shared aka customer or share
        user (if any partner), the channel ID (if any) and the list of followed
        subtypes.

         :param doc_data: list of documents to fetch their followers. It is a list
         of tuples (res_model, res_ids), where res_model is a document model and
         res_ids the ids of documents.

         :return: list of followers data which is a list of tuples (partner_id
         (void if channel_id), channel_id (void if partner_id), partner is share
         (aka no user or shared user, void id channel_id), list of followed subtype
         ids)
        """
        where_clause = ' OR '.join(['fol.res_model = %s AND fol.res_id = ANY(%s)'] * len(doc_data))
        where_params = list(itertools.chain.from_iterable((res_model, res_ids) for res_model, res_ids in doc_data))
        query = """
SELECT fol.partner_id, fol.channel_id, partner.partner_share, array_agg(subtype.id)
FROM mail_followers fol
LEFT JOIN res_partner partner ON partner.id = fol.partner_id
LEFT JOIN mail_followers_mail_message_subtype_rel fol_rel ON fol_rel.mail_followers_id = fol.id
LEFT JOIN mail_message_subtype subtype ON subtype.id = fol_rel.mail_message_subtype_id
WHERE %s
GROUP BY fol.id, partner.partner_share""" % where_clause
        self.env.cr.execute(query, where_params)
        return self.env.cr.fetchall()

    # --------------------------------------------------
    # Private tools methods to generate new subscription
    # --------------------------------------------------

    def _insert_followers(self, res_model, res_ids, partner_ids, partner_subtypes, channel_ids, channel_subtypes,
                          is_customer_ids=None, check_existing=False, existing_policy='skip'):
        sudo_self = self.sudo()
        created_ids = list()
        if not partner_subtypes and not channel_subtypes:  # no subtypes -> default computation, no force, skip existing
            new, upd = self._add_default_followers(res_model, res_ids, partner_ids, channel_ids, is_customer_ids=is_customer_ids)
        else:
            new, upd = self._add_follower_new(res_model, res_ids, partner_ids, partner_subtypes, channel_ids, channel_subtypes, check_existing=check_existing, existing_policy=existing_policy)
        for res_id, values_list in new.items():
            for values in values_list:
                created_ids.append(sudo_self.create(dict(values, res_id=res_id)).id)
        for fol_id, values in upd.items():
            sudo_self.browse(fol_id).write(values)
        return created_ids

    def _add_default_followers(self, res_model, res_ids, partner_ids, channel_ids=None, is_customer_ids=None):
        """ Private shortcut to add partner ids as follower of documents given
        their res_model and res_ids. It will compute default subtypes and avoid
        updating existing followers. """
        if not partner_ids and not channel_ids:
            return dict(), dict()
        channel_ids = channel_ids or []

        default, _, external = self.env['mail.message.subtype'].default_subtypes(res_model)
        if partner_ids and is_customer_ids is None:
            is_customer_ids = self.env['res.partner'].sudo().search([('id', 'in', partner_ids), ('partner_share', '=', True)]).ids

        c_stypes = dict.fromkeys(channel_ids, default.ids)
        p_stypes = dict((pid, external.ids if pid in is_customer_ids else default.ids) for pid in partner_ids)

        return self._add_follower_new(res_model, res_ids, partner_ids, p_stypes, channel_ids, c_stypes, check_existing=True, existing_policy='skip')

    def _add_follower_new(self, res_model, res_ids, partner_ids, partner_subtypes, channel_ids, channel_subtypes,
                          check_existing=False, existing_policy='skip'):
        """ Internal method that generates values to insert or update followers.
        Callers have to handle the result, for example by making a valid ORM
        command, inserting or updating directly follower records, ...

        This method returns two main data

         * first one is a dict which keys are res_ids. Value is a list of dict of
           values valid for creating new followers for the related res_id;
         * second one is a dict which keys are follower ids. Value is a dict of
           values valid for updating the related follower record;

         :param check_existing: if True, check for existing followers for given
         documents and handle them according to existing_policy parameter. If False
         it bypasses the check. If allows to save some computation if caller is sure
         there are no conflict for followers;
         :param existing policy: if check_existing is True, tells what to do with
         already-existing followers:

          * skip: simply skip existing followers, do not touch them;
          * unlink: unlink existing followers, meaning given values will create
            new one for all conflicting followers (aka armageddon)
          * update: give new subtypes, meaning an update dict will be generated
            to add missing subtypes; no subtypes will ever be removed
        """
        doc_pids, doc_cids = dict((res_id, set()) for res_id in res_ids or [0]), dict((res_id, set()) for res_id in res_ids or [0])
        data_pids, data_cids = dict(), dict()

        new, update = dict(), dict()
        if check_existing and res_ids:
            prout = self._get_followers_data(res_model, res_ids, partner_ids or [], channel_ids or [])
            for fid, rid, pid, cid, sids in prout:
                if pid:
                    if existing_policy != 'unlink':
                        doc_pids[rid].add(pid)
                    data_pids[fid] = (rid, pid, sids)
                elif cid:
                    if existing_policy != 'unlink':
                        doc_cids[rid].add(cid)
                    data_cids[fid] = (rid, cid, sids)

            if existing_policy == 'unlink':
                self.sudo().browse(list(data_pids.keys()) + list(data_cids.keys())).unlink()

        for res_id in res_ids or [0]:
            for partner_id in set(partner_ids or []):
                if partner_id not in doc_pids[res_id]:
                    new.setdefault(res_id, list()).append({
                        'res_model': res_model,
                        'partner_id': partner_id,
                        'subtype_ids': [(6, 0, partner_subtypes[partner_id])],
                    })
                elif existing_policy == 'update':
                    fol_id, sids = next(((key, val[2]) for key, val in data_pids.items() if val[0] == res_id), (False, []))
                    new_sids = set(partner_subtypes[partner_id]) - set(sids)
                    if not fol_id or not new_sids:
                        continue
                    if new_sids:
                        update[fol_id] = {
                            'subtype_ids': [(4, sid) for sid in new_sids]
                        }
            for channel_id in set(channel_ids or []):
                if channel_id not in doc_cids[res_id]:
                    new.setdefault(res_id, list()).append({
                        'res_model': res_model,
                        'channel_id': channel_id,
                        'subtype_ids': [(6, 0, channel_subtypes[channel_id])],
                    })
                elif existing_policy == 'update':
                    fol_id, sids = next(((key, val[2]) for key, val in data_cids.items() if val[0] == res_id), (False, []))
                    new_sids = set(channel_subtypes[channel_id]) - set(sids)
                    if not fol_id or not new_sids:
                        continue
                    if new_sids:
                        update[fol_id] = {
                            'subtype_ids': [(4, sid) for sid in new_sids]
                        }

        return new, update
