# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 - KMEE INFORMATICA LTDA (<http://kmee.com.br>).
#              Luis Felipe Miléo - mileo@kmee.com.br
#
#    All other contributions are (C) by their respective contributors
#
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _


class PaymentOrderCreate(models.TransientModel):
    _inherit = 'payment.order.create'

    schedule_date = fields.Date('Data Programada')
    all_posted_moves = fields.Boolean(u'Títulos em aberto', default=True)

    @api.model
    def default_get(self, field_list):
        res = super(PaymentOrderCreate, self).default_get(field_list)
        context = self.env.context
        if ('entries' in field_list and context.get('line_ids') and
                context.get('populate_results')):
            res.update({'entries': context['line_ids']})
        return res

    @api.multi
    def extend_payment_order_domain(self, payment_order, domain):
        self.ensure_one()

        # Search for all posted moves
        if self.all_posted_moves:
            pass
            # TODO Implementar a pesquisa correta

        if payment_order.payment_order_type == 'payment':
            # For payables, propose all unreconciled credit lines,
            # including partially reconciled ones.
            # If they are partially reconciled with a supplier refund,
            # the residual will be added to the payment order.
            #
            # For receivables, propose all unreconciled credit lines.
            # (ie customer refunds): they can be refunded with a payment.
            # Do not propose partially reconciled credit lines,
            # as they are deducted from a customer invoice, and
            # will not be refunded with a payment.
            domain += [('credit', '>', 0),
                       '|',
                       ('account_id.type', '=', 'payable'),
                       '&',
                       ('account_id.type', '=', 'receivable'),
                       ('reconcile_partial_id', '=', False)]

    @api.multi
    def filter_lines(self, lines):
        """ Filter move lines before proposing them for inclusion
            in the payment order.

        This implementation filters out move lines that are already
        included in draft or open payment orders. This prevents the
        user to include the same line in two different open payment
        orders. When the payment order is sent, it is assumed that
        the move will be reconciled soon (or immediately with
        account_banking_payment_transfer), so it will not be
        proposed anymore for payment.

        See also https://github.com/OCA/bank-payment/issues/93.

        :param lines: recordset of move lines
        :returns: list of move line ids
        """
        self.ensure_one()
        payment_lines = self.env['payment.line'].\
            search([('order_id.state', 'in', ('draft', 'open', 'done')),
                    ('move_line_id', 'in', lines.ids)])
        to_exclude = set([l.move_line_id.id for l in payment_lines])
        return [l.id for l in lines if l.id not in to_exclude]

    @api.multi
    def search_entries(self):
        """This method taken from account_payment module.
        We adapt the domain based on the payment_order_type
        """
        line_obj = self.env['account.move.line']
        model_data_obj = self.env['ir.model.data']
        # -- start account_banking_payment --
        payment = self.env['payment.order'].browse(
            self.env.context['active_id'])
        # Search for move line to pay:
        domain = [('move_id.state', '=', 'posted'),
                  ('reconcile_id', '=', False),
                  ('company_id', '=', payment.mode.company_id.id),
                  '|',
                  ('date_maturity', '<=', self.duedate),
                  ('date_maturity', '=', False)]
        self.extend_payment_order_domain(payment, domain)
        # -- end account_direct_debit --
        lines = line_obj.search(domain)
        context = self.env.context.copy()
        context['line_ids'] = self.filter_lines(lines)
        context['populate_results'] = self.populate_results
        if payment.payment_order_type == 'payment':
            context['display_credit'] = True
            context['display_debit'] = False
        else:
            context['display_credit'] = False
            context['display_debit'] = True
        model_datas = model_data_obj.search(
            [('model', '=', 'ir.ui.view'),
             ('name', '=', 'view_create_payment_order_lines')])
        return {'name': _('Entry Lines'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.order.create',
                'views': [(model_datas[0].res_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    @api.multi
    def _prepare_payment_line(self, payment, line):
        res = super(PaymentOrderCreate, self)._prepare_payment_line(payment,
                                                                    line)
        if payment.payment_order_type == 'cobranca':
            res['amount_currency'] *= -1
        if line.invoice:
            if line.invoice.type in ('in_invoice', 'in_refund'):
                if line.invoice.reference_type == 'structured':
                    res['state'] = 'structured'
                    res['communication'] = line.invoice.reference
                else:
                    if line.invoice.reference:
                        res['communication'] = line.invoice.reference
                    elif line.invoice.supplier_invoice_number:
                        res['communication'] = \
                            line.invoice.supplier_invoice_number
            else:
                # Make sure that the communication includes the
                # customer invoice number (in the case of debit order)
                res['communication'] = line.name
                res['state'] = 'structured'

        return res
