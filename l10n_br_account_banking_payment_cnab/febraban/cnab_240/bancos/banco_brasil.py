# -*- coding: utf-8 -*-
# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from ..cnab_240 import Cnab240
from openerp.exceptions import Warning as UserError


class BancoBrasil240(Cnab240):

    def __init__(self):
        super(Cnab240, self).__init__()
        from cnab240.bancos import banco_brasil
        self.bank = banco_brasil

    def _prepare_header(self):
        codigo_convenio = str(self.order.mode.boleto_convenio).zfill(9)
        cobranca_cedente = '0014'
        carteira = self.order.mode.boleto_carteira[:2]
        variacao = self.order.mode.boleto_variacao.zfill(3)
        vals = super(BancoBrasil240, self)._prepare_header()
        vals['controlecob_numero'] = self.order.id
        vals['controlecob_data_gravacao'] = self.data_hoje()
        vals['nome_do_banco'] = 'BANCO DO BRASIL S.A.'
        vals['codigo_convenio_banco'] = codigo_convenio + cobranca_cedente +\
            carteira + variacao + "  "
        vals['cedente_conta_dv'] = int(self.order.mode.bank_id.acc_number_dig)
        return vals

    def _prepare_segmento(self, line):
        codigo_convenio = str(line.env['payment.mode'].search([]).
                              boleto_convenio).zfill(9)
        cobranca_cedente = '0014'
        carteira = line.env['payment.mode'].search([]).boleto_carteira[:2]
        variacao = line.env['payment.mode'].search([]).boleto_variacao.zfill(3)
        protesto = int(line.env['payment.mode'].search([]).boleto_protesto)
        if protesto == 3:
            dias_protesto = 0
        if protesto != 1 or protesto != 2 or protesto != 3:
            protesto = 3
            dias_protesto = 0
        else:
            dias_protesto = int(line.env['payment.mode'].search([]).
                                boleto_protesto_prazo)
        conta = int(line.env['payment.mode'].search([]).bank_id.acc_number)
        dv_conta = int(line.env['payment.mode'].search([]).
                       bank_id.acc_number_dig)
        vals = super(BancoBrasil240, self)._prepare_segmento(line)
        if line.move_line_id.transaction_ref:
            nossonumero, digito = self.nosso_numero(
                line.move_line_id.transaction_ref)
        else:
            raise UserError('Esta cobrança não possui um boleto associado.')
        # parcela = line.move_line_id.name.split('/')[1]
        # vals['cedente_convenio'] = self.format_codigo_convenio_banco(line)
        vals['carteira_numero'] = int(line.order_id.mode.boleto_carteira[:2])
        vals['nosso_numero'] = ""  # self.format_nosso_numero(
        # nossonumero, digito, parcela, line.order_id.mode.boleto_modalidade)
        # Tipo de convenio 1: nosso_numero vazio pois o banco numera, emite e
        # expede TODO: para outros tipos, formatar o nosso numero
        # apropriadamente
        vals['codigo_protesto'] = protesto
        vals['prazo_protesto'] = dias_protesto
        vals['nosso_numero_dv'] = int(digito)
        vals['prazo_baixa'] = '0'
        vals['controlecob_numero'] = self.order.id
        vals['controlecob_data_gravacao'] = self.data_hoje()
        vals['numero_conta_corrente'] = conta
        vals['numero_conta_corrente_dv'] = dv_conta
        vals['cedente_convenio'] = codigo_convenio + cobranca_cedente +\
            carteira + variacao + "  "
        return vals

    def nosso_numero(self, format):
        digito = format[-1:]
        nosso_numero = format[2:-2]
        return nosso_numero, digito

    def format_nosso_numero(self, nosso_numero, digito, parcela, modalidade):
        return "%s%s%s%s4     " % (nosso_numero.zfill(9), digito,
                                   parcela.zfill(2), modalidade)

    def format_codigo_convenio_banco(self, line):
        num_convenio = line.order_id.mode.boleto_convenio
        carteira = line.order_id.mode.boleto_carteira[:2]
        boleto = line.order_id.mode.boleto_variacao.zfill(3)
        return "%s0014%s%s  " % (num_convenio, carteira, boleto)
