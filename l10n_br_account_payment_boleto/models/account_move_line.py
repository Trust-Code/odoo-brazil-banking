# -*- coding: utf-8 -*-
##############################################################################
#
#    Account Payment Boleto module for Odoo
#    Copyright (C) 2012-2015 KMEE (http://www.kmee.com.br)
#    @author Luis Felipe Miléo <mileo@kmee.com.br>
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

import logging
from openerp import models, fields, api
from openerp.exceptions import Warning as UserError
from datetime import date
from ..boleto.document import Boleto
from ..boleto.document import BoletoException

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    date_payment_created = fields.Date(
        u'Data da criação do pagamento', readonly=True)
    boleto_own_number = fields.Char(
        u'Nosso Número', readonly=True)

    @api.multi
    def validate_boleto_config(self):
        error_list = []
        for move_line in self:
            if not move_line.partner_id.legal_name:
                error_list.append(
                    u"Razão social/Nome do cliente não está definido")
            if not move_line.partner_id.district:
                error_list.append(u"Bairro do cliente não está definido")
            if not move_line.partner_id.country_id.id:
                error_list.append(u"País do cliente não está definido")
            if not move_line.partner_id.l10n_br_city_id.name:
                error_list.append(u"Cidade do cliente não está definida")
            if not move_line.partner_id.street:
                error_list.append(u"Nome da rua do cliente não está definida")
            if not move_line.partner_id.number:
                error_list.append(
                    u"Número da residência do cliente não está definida")
            if move_line.payment_mode_id.type_sale_payment != '00':
                error_list.append(
                    u"In payment mode %s Tipo SPED must be 00 - Duplicata" %
                    move_line.payment_mode_id.name)
            if not move_line.payment_mode_id.internal_sequence_id:
                error_list.append(u"Please set sequence in payment mode %s" %
                                  move_line.payment_mode_id.name)
            if not move_line.payment_mode_id.boleto_type:
                error_list.append(
                    u"Configure o tipo de boleto no modo de pagamento")
            if not move_line.payment_mode_id.boleto_carteira:
                error_list.append(u"Carteira not set in payment method")
            if not move_line.payment_mode_id.instrucoes:
                error_list.append(u"Campo de instruções vazio")
            if move_line.payment_mode_id.instrucoes and \
               len(move_line.payment_mode_id.instrucoes) > 90:
                error_list.append(
                    u"Campo de instruções excedeu o limite de 90 caracteres")
            if len(error_list) > 0:
                error_string = "\n".join(error_list)
                raise UserError('Atenção!', error_string)
            return True

    @api.multi
    def generate_draft_payment_order(self):
        """Gera um objeto de payment.order ao imprimir um boleto"""
        payment_order = self.env['payment.order'].search([
            ('state', '=', 'draft'),
            ('payment_order_type', '=', 'cobranca')], limit=1)
        if not payment_order:
            order_dict = {
                'user_id': self.env.user.id,
                'mode': self.payment_mode_id.id,
                'date_maturity': self.date_maturity,
                'state': 'draft',
                'payment_order_type': 'cobranca',
            }
            payment_order = self.env['payment.order'].create(order_dict)

        lines = self.env['payment.line'].search(
            [('move_line_id', '=', self.id)])
        if not lines:
            wiz_order = self.env['payment.order.create'].with_context(
                active_model='payment.order', active_id=payment_order.id
            ).create({'date_type': 'due'})
            vals = wiz_order._prepare_payment_line(payment_order, self)
            self.env['payment.line'].create(vals)

    @api.multi
    def send_payment(self):
        boleto_list = []

        self.validate_boleto_config()
        for move_line in self:
            if move_line.payment_mode_id.type_sale_payment == '00':
                number_type = move_line.company_id.own_number_type
                if not move_line.boleto_own_number:
                    if number_type == '0':
                        nosso_numero = self.env['ir.sequence'].next_by_id(
                            move_line.company_id.own_number_sequence.id)
                    elif number_type == '1':
                        nosso_numero = \
                            move_line.transaction_ref.replace('/', '')
                    else:
                        nosso_numero = self.env['ir.sequence'].next_by_id(
                            move_line.payment_mode_id.
                            internal_sequence_id.id)
                else:
                    nosso_numero = move_line.boleto_own_number

                boleto = Boleto.getBoleto(move_line, nosso_numero)
                if boleto:
                    move_line.date_payment_created = date.today()
                    move_line.transaction_ref = \
                        boleto.boleto.format_nosso_numero()
                    move_line.boleto_own_number = nosso_numero

                boleto_list.append(boleto.boleto)
                move_line.generate_draft_payment_order()
        return boleto_list
