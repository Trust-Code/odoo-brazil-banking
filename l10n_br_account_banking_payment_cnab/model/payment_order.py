# -*- coding: utf-8 -*-
# #############################################################################
#
#
#    Copyright (C) 2012 KMEE (http://www.kmee.com.br)
#    @author Fernando Marcato Rodrigues
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

from openerp import models, fields, api
from openerp.exceptions import Warning as UserError


class PaymentOrder(models.Model):
    _inherit = 'payment.order'

    file_number = fields.Integer(u'Número sequencial do arquivo')
    # TODO adicionar domain para permitir o modo de pagamento correspondente
    # ao mode

    sufixo_arquivo = fields.Integer(u'Sufixo do arquivo')
    serie_sufixo_arquivo = fields.Many2one(
        'l10n_br_cnab_file_sufix.sequence', u'Série do Sufixo do arquivo')

    @api.model
    def get_next_number(self):
        if not self.mode.cnab_sequence_id:
            raise UserError(
                'Atenção!',
                'Configure a sequência do CNAB no modo de pagamento')
        return self.env['ir.sequence'].next_by_id(
            self.mode.cnab_sequence_id.id)

    def get_next_sufixo(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for ord in self.browse(cr, uid, ids):
            sequence = self.pool.get('ir.sequence')
            # sequence_read = sequence.read(
            #     cr, uid, ord.serie_id.internal_sequence_id.id,
            #     ['number_next'])
            seq_no = sequence.get_id(
                cr, uid,
                ord.serie_sufixo_arquivo.internal_sequence_id.id,
                context=context)
            self.write(cr, uid, ord.id, {'sufixo_arquivo': seq_no})
        return seq_no
