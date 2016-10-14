# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Fernando Marcato Rodrigues
#    Copyright (C) 2015 KMEE - www.kmee.com.br
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import StringIO
from decimal import Decimal
from openerp import api, models, fields
from .file_cnab240_parser import Cnab240Parser as cnabparser


_logger = logging.getLogger(__name__)


MODOS_IMPORTACAO_CNAB = [
    ('sicoob_240', u'Sicoob Cobrança 240'),
    ('cecred_240', u'CECRED 240'),
]


class AccountBankStatementImport(models.TransientModel):
    """  """
    _inherit = 'account.bank.statement.import'

    import_modes = fields.Selection(
        MODOS_IMPORTACAO_CNAB,
        string=u'Opções de importação', select=True, required=True)

    @api.model
    def _find_bank_account_id(self, account_number):
        """ Get res.partner.bank ID """
        bank_account_id = None
        if account_number:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', str(account_number))], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0].id
        return bank_account_id

    @api.model
    def _complete_statement(self, stmt_vals, journal_id, account_number):
        """Complete statement from information passed.
            unique_import_id is assumed to already be unique at the moment of
            CNAB exportation."""
        stmt_vals['journal_id'] = journal_id
        journal = self.env['account.journal'].browse(journal_id)
        if journal.with_last_closing_balance:
            start = self.env['account.bank.statement']\
                ._compute_balance_end_real(journal_id)
            stmt_vals['balance_start'] = Decimal("%.4g" % start)
            stmt_vals['balance_end_real'] += Decimal("%.4g" % start)

        for line_vals in stmt_vals['transactions']:
            unique_import_id = line_vals.get('unique_import_id', False)
            if unique_import_id:
                moves = self.env['account.move.line'].search(
                    [('transaction_ref', '=', unique_import_id)])
                if moves:
                    line_vals['partner_id'] = moves[0].partner_id.id
        return stmt_vals

    @api.multi
    def _parse_file(self, data_file):
        """Parse a CNAB file."""
        self.ensure_one()
        parser = cnabparser()
        try:
            _logger.debug("Try parsing with CNAB.")
            vals = parser.parse(data_file, self.import_modes)
            if self.journal_id:
                bank_account = self.env['res.partner.bank'].search(
                    [('journal_id', '=', self.journal_id.id)], limit=1)

                vals[0]['account_number'] = bank_account.acc_number
            return vals
        except ValueError:
            # Not a CNAB file, returning super will call next candidate:
            _logger.debug("Statement file was not a CNAB  file.",
                          exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
