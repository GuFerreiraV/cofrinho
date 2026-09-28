from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from html import escape

from bot.models import Despesa
from bot.services.categorizacao_service import CATEGORIAS, icone

MESES = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)  # fmt: skip

ICONES_PAGAMENTO = {"Pix": "⚡", "Débito": "💳", "Crédito": "💳", "Dinheiro": "💵"}


def formatar_brl(valor: Decimal) -> str:
    """Decimal('1234.5') → 'R$ 1.234,50' (sem depender de locale do SO)."""
    valor = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sinal = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sinal}R$ {texto}"


def formatar_data(data: date) -> str:
    return data.strftime("%d/%m/%Y")


def nome_mes(data: date) -> str:
    return f"{MESES[data.month - 1]}/{data.year}"


def formatar_confirmacao(despesa: Despesa, titulo: str = "✅ Gasto registrado!") -> str:
    return (
        f"<b>{titulo}</b>\n\n"
        f"💰 <b>Valor:</b> {formatar_brl(despesa.valor)}\n"
        f"💳 <b>Pagamento:</b> {escape(despesa.forma_pagamento)}\n"
        f"📅 <b>Data:</b> {formatar_data(despesa.data)}\n"
        f"📝 <b>Descrição:</b> {escape(despesa.descricao)}\n"
        f"{icone(despesa.categoria)} <b>Categoria:</b> {escape(despesa.categoria)}"
    )


def formatar_relatorio(titulo: str, totais: dict[str, Decimal]) -> str:
    """Resumo por categoria no layout do escopo, em bloco monoespaçado."""
    linhas_categorias = [(f"{icone(c)} {c}", totais.get(c, Decimal("0"))) for c in CATEGORIAS]
    # Categorias fora da lista padrão (não deveria acontecer) entram no fim
    linhas_categorias += [(f"📦 {c}", v) for c, v in totais.items() if c not in CATEGORIAS]
    total = sum((v for _, v in linhas_categorias), Decimal("0"))

    linhas = [*linhas_categorias, ("💵 Total", total)]
    largura_rotulo = max(len(rotulo) for rotulo, _ in linhas)
    largura_valor = max(len(formatar_brl(v)) for _, v in linhas)

    def linha(rotulo: str, valor: Decimal) -> str:
        return f"{rotulo.ljust(largura_rotulo)} {formatar_brl(valor).rjust(largura_valor)}"

    corpo = [linha(r, v) for r, v in linhas_categorias]
    corpo.append("─" * (largura_rotulo + largura_valor + 1))
    corpo.append(linha("💵 Total", total))
    return f"<b>{escape(titulo)}</b>\n<pre>{escape(chr(10).join(corpo))}</pre>"


def erro(mensagem: str) -> str:
    return f"❌ {mensagem}"


def alerta(mensagem: str) -> str:
    return f"⚠️ {mensagem}"
