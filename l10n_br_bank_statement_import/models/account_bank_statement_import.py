# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 Trustcode - www.trustcode.com.br                         #
#              Danimar Ribeiro <danimaribeiro@gmail.com>                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import logging
import StringIO
from openerp import api, models
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError
_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser as ofxparser
except ImportError:
    _logger.warn("ofxparse not found, OFX parsing disabled.")
    ofxparser = None


class AccountBankStatementImport(models.TransientModel):
    """Extend model account.bank.statement."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _find_bank_account_id(self, account_number):
        """ Get res.partner.bank ID """
        bank_account_id = None
        if account_number and len(account_number) > 4:
            sql = """select id from res_partner_bank
                where (acc_number = %s) or ((bra_number || acc_number) = %s)"""

            self.env.cr.execute(sql, [account_number, account_number])
            res = self.env.cr.fetchone()
            if res:
                bank_account_id = res[0]
        return bank_account_id

    try:
        from ofxparse import OfxParser as ofxparser
    except ImportError:
        _logger.warn("ofxparse not found, OFX parsing disabled.")
        ofxparser = None

    @api.model
    def _check_ofx(self, data_file):
        if ofxparser is None:
            return False
        try:
            data_file = data_file.replace('\r\n', '\n').replace('\r', '\n')
            ofx = ofxparser.parse(StringIO.StringIO(data_file))
        except:
            return False
        return ofx

    @api.model
    def _parse_file(self, data_file):
        ofx = self._check_ofx(data_file)
        if not ofx:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        transactions = []
        total_amt = 0.00
        try:
            indice = 1
            for transaction in ofx.account.statement.transactions:
                # Since ofxparse doesn't provide account numbers, we'll have
                # to find res.partner and res.partner.bank here
                # (normal behavious is to provide 'account_number', which the
                # generic module uses to find partner/bank)
                bank_account_id = partner_id = False
                if transaction.payee:
                    banks = self.env['res.partner.bank'].search(
                        [('owner_name', '=', transaction.payee)], limit=1)
                    if banks:
                        bank_account = banks[0]
                        bank_account_id = bank_account.id
                        partner_id = bank_account.partner_id.id

                vals_line = {
                    'date': transaction.date,
                    'name': transaction.payee + (
                        transaction.memo and ': ' + transaction.memo or ''),
                    'ref': transaction.id,
                    'amount': transaction.amount,
                    'unique_import_id': '%s-%s-%s-%s' % (
                        indice,
                        transaction.id,
                        transaction.payee,
                        transaction.memo),
                    'bank_account_id': bank_account_id,
                    'partner_id': partner_id,
                }

                indice += 1
                # Memo (<NAME>) and payee (<PAYEE>) are not required
                # field in OFX statement, cf section 11.4.3 Statement
                # Transaction <STMTTRN> of the OFX specs: the required
                # elements are in bold, cf 1.5 Conventions and these 2
                # fields are not in bold.
                # But the 'name' field of account.bank.statement.line is
                # required=True, so we must always have a value !
                # The field TRNTYPE is a required field in OFX
                if not vals_line['name']:
                    vals_line['name'] = transaction.type.capitalize()
                    if transaction.checknum:
                        vals_line['name'] += ' %s' % transaction.checknum
                total_amt += float(transaction.amount)
                transactions.append(vals_line)
        except Exception, e:
            raise UserError(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e.message
            ))

        vals_bank_statement = {
            'name': ofx.account.number,
            'transactions': transactions,
            'balance_start': ofx.account.statement.balance,
            'balance_end_real':
                float(ofx.account.statement.balance) + total_amt,
        }
        account = ofx.account.number
        if self.journal_id:
            bank_account = self.env['res.partner.bank'].search(
                [('journal_id', '=', self.journal_id.id)], limit=1)

            account = bank_account.acc_number
        return ofx.account.statement.currency, account, [
            vals_bank_statement]
