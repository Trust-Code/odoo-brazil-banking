# coding: utf-8
# ###########################################################################
#
#    Author: Luis Felipe Mileo
#            Luiz Felipe do Divino
#    Copyright 2015 KMEE - www.kmee.com.br
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

from openerp import models, fields


class PaymentMode(models.Model):
    _inherit = "payment.mode"

    gnre_value_field = fields.Many2one(
        'ir.model.fields', 'Value field',
        domain=[('model_id', '=', 'account.invoice')])
    gnre_type = fields.Many2one('l10n_br_tax.gnre')


class PaymentModeType(models.Model):
    _inherit = 'payment.mode.type'
    _description = 'Payment Mode Type'

    payment_order_type = fields.Selection(
        selection_add=[
            ('tax', u'Tributos'),
        ])


class PaymentOrder(models.Model):
    _inherit = 'payment.order'

    payment_order_type = fields.Selection(
        selection_add=[
            ('tax', u'Tributos'),
        ])


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    has_gnre = fields.Boolean(
        related='stored_invoice_id.has_gnre',
        string="Tem GNRE")
