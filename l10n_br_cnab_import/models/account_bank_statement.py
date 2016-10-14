# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model
    def get_reconciliation_proposition(self, st_line, excluded_ids=None):
        res = super(AccountBankStatementLine, self).\
            get_reconciliation_proposition(st_line, excluded_ids)
        moves = self.env['account.move.line'].search(
            [('transaction_ref', '=', st_line.unique_import_id)])
        if moves:
            target_currency = st_line.currency_id or \
                st_line.journal_id.currency or \
                st_line.journal_id.company_id.currency_id
            mv_line = self.env['account.move.line'].\
                prepare_move_lines_for_reconciliation_widget(
                    moves, target_currency=target_currency,
                    target_date=st_line.date)
            for line in mv_line:
                line['name'] = '%s %s' % (line['partner_name'], line['name'])
            return mv_line
        return res
