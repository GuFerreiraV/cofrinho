from datetime import date
from decimal import Decimal

import pytest

from bot.services.parser_service import (
    MAX_DESCRICAO,
    limpar_descricao,
    parse,
    parse_data,
    parse_forma_pagamento,
    parse_valor,
)

HOJE = date(2026, 9, 26)  # sábado


def test_frase_completa_em_linguagem_natural():
    p = parse("Gastei 45 reais no mercado com débito hoje", HOJE)
    assert p.valor == Decimal("45.00")
    assert p.forma_pagamento == "Débito"
    assert p.data == HOJE
    assert p.descricao == "Mercado"


def test_comando_estruturado_com_aspas():
    p = parse('45 debito "mercado do bairro"', HOJE)
    assert p.valor == Decimal("45.00")
    assert p.forma_pagamento == "Débito"
    assert p.descricao == "Mercado do bairro"


def test_valor_com_virgula_e_pix():
    p = parse("45,90 pix ifood", HOJE)
    assert p.valor == Decimal("45.90")
    assert p.forma_pagamento == "Pix"
    assert p.descricao == "Ifood"


def test_valor_com_milhar_e_data_com_barra():
    p = parse("R$ 1.234,56 crédito notebook 05/09", HOJE)
    assert p.valor == Decimal("1234.56")
    assert p.forma_pagamento == "Crédito"
    assert p.data == date(2026, 9, 5)
    assert p.descricao == "Notebook"


def test_data_nao_vira_valor():
    p = parse("05/09 mercado", HOJE)
    assert p.valor is None
    assert p.data == date(2026, 9, 5)


def test_ontem_e_dinheiro():
    p = parse("ontem 30 dinheiro padaria", HOJE)
    assert p.valor == Decimal("30.00")
    assert p.forma_pagamento == "Dinheiro"
    assert p.data == date(2026, 9, 25)
    assert p.descricao == "Padaria"


def test_cartao_de_credito_vence_cartao():
    p = parse("120 no cartão de crédito cinema", HOJE)
    assert p.forma_pagamento == "Crédito"
    assert p.descricao == "Cinema"


def test_descricao_mantem_preposicoes_do_meio():
    p = parse("comprei livro de python 89,90 no pix", HOJE)
    assert p.descricao == "Livro de python"
    assert p.valor == Decimal("89.90")


def test_campos_faltando_ficam_none():
    p = parse("mercado", HOJE)
    assert p.valor is None
    assert p.forma_pagamento is None
    assert p.data == HOJE
    assert p.descricao == "Mercado"


def test_texto_vazio():
    p = parse("", HOJE)
    assert (p.valor, p.forma_pagamento, p.descricao) == (None, None, None)
    assert p.data == HOJE


def test_data_invalida_vira_none():
    assert parse("50 pix 31/02 mercado", HOJE).data is None


def test_data_sem_ano_no_futuro_vai_para_o_ano_anterior():
    assert parse("10 pix 20/12 presente", HOJE).data == date(2025, 12, 20)


def test_dia_do_mes():
    assert parse("dia 5 mercado 30 pix", HOJE).data == date(2026, 9, 5)
    assert parse("dia 5 mercado 30 pix", HOJE).valor == Decimal("30.00")
    assert parse("dia 28 mercado 30 pix", HOJE).data == date(2026, 8, 28)


def test_data_por_extenso():
    assert parse("50 pix 5 de setembro mercado", HOJE).data == date(2026, 9, 5)


def test_numero_dentro_de_palavra_nao_vira_valor():
    p = parse("ps5 2500 credito", HOJE)
    assert p.valor == Decimal("2500.00")
    assert p.descricao == "Ps5"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("45", Decimal("45.00")),
        ("45,9", Decimal("45.90")),
        ("45.90", Decimal("45.90")),
        ("R$10", Decimal("10.00")),
        ("1.500", Decimal("1500.00")),
        ("0", None),
        ("abc", None),
    ],
)
def test_parse_valor(texto, esperado):
    assert parse_valor(texto) == esperado


def test_parse_forma_pagamento():
    assert parse_forma_pagamento("Debito") == "Débito"
    assert parse_forma_pagamento("espécie") == "Dinheiro"
    assert parse_forma_pagamento("boleto") is None


def test_parse_data_avulsa():
    assert parse_data("ontem", HOJE) == date(2026, 9, 25)
    assert parse_data("qualquer coisa", HOJE) is None


def test_descricao_acima_do_limite_vira_none():
    assert limpar_descricao("a" * MAX_DESCRICAO) == "A" + "a" * (MAX_DESCRICAO - 1)
    assert limpar_descricao("a" * (MAX_DESCRICAO + 1)) is None


def test_limpar_descricao():
    assert limpar_descricao("  no mercado com  ") == "Mercado"
    assert limpar_descricao("com o") is None


@pytest.mark.parametrize(
    "texto",
    ["voucher", "Voucher", "VR", "va", "vale refeição", "vale-alimentação", "cartão voucher"],
)
def test_sinonimos_de_voucher(texto):
    assert parse_forma_pagamento(texto) == "Voucher"


def test_voucher_em_frase():
    p = parse("35 no restaurante com o vale refeição", HOJE)
    assert p.forma_pagamento == "Voucher"
    assert p.descricao == "Restaurante"


def test_cartao_voucher_nao_vira_credito_nem_sobra_na_descricao():
    p = parse("40 almoço cartão voucher", HOJE)
    assert p.forma_pagamento == "Voucher"
    assert p.descricao == "Almoço"


def test_palavra_com_va_no_meio_nao_vira_voucher():
    assert parse_forma_pagamento("vaso") is None
    assert parse_forma_pagamento("uva") is None
