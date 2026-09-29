from decimal import Decimal

from bot.services.formatador_service import formatar_brl, formatar_relatorio


def test_formatar_brl():
    assert formatar_brl(Decimal("1234.5")) == "R$ 1.234,50"
    assert formatar_brl(Decimal("0")) == "R$ 0,00"
    assert formatar_brl(Decimal("45")) == "R$ 45,00"
    assert formatar_brl(Decimal("1234567.891")) == "R$ 1.234.567,89"


def test_formatar_relatorio_lista_todas_as_categorias_e_total():
    texto = formatar_relatorio(
        "📊 Resumo de Setembro/2026",
        {"Comida": Decimal("890.50"), "Lazer": Decimal("320.00")},
    )
    assert texto.startswith("<b>📊 Resumo de Setembro/2026</b>\n<pre>")
    for rotulo in ("🎮 Lazer", "📚 Estudos", "🍔 Comida", "📈 Investimentos", "📦 Outros"):
        assert rotulo in texto
    assert "R$ 890,50" in texto
    assert "R$ 0,00" in texto
    assert "💵 Total" in texto and "R$ 1.210,50" in texto


def test_formatar_relatorio_alinha_valores():
    texto = formatar_relatorio("x", {"Comida": Decimal("1000"), "Lazer": Decimal("5")})
    corpo = texto.split("<pre>")[1].removesuffix("</pre>")
    linhas = [linha for linha in corpo.splitlines() if "R$" in linha]
    assert len({len(linha) for linha in linhas}) == 1


def test_toda_forma_de_pagamento_tem_icone():
    from bot.services.formatador_service import ICONES_PAGAMENTO
    from bot.services.parser_service import FORMAS_PAGAMENTO

    assert set(FORMAS_PAGAMENTO) <= set(ICONES_PAGAMENTO)
