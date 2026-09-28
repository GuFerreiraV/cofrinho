import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import dateparser

VALOR_MAXIMO = Decimal("99999999.99")  # limite de Numeric(10, 2)

FORMAS_PAGAMENTO = ("Pix", "Débito", "Crédito", "Dinheiro")

# Padrões mais longos primeiro, para "cartão de crédito" vencer "cartão"
_SINONIMOS_PAGAMENTO: list[tuple[str, str]] = [
    (r"cart[aã]o\s+de\s+d[eé]bito", "Débito"),
    (r"cart[aã]o\s+de\s+cr[eé]dito", "Crédito"),
    (r"d[eé]bito", "Débito"),
    (r"cr[eé]dito", "Crédito"),
    (r"cart[aã]o", "Crédito"),
    (r"pix", "Pix"),
    (r"dinheiro", "Dinheiro"),
    (r"esp[eé]cie", "Dinheiro"),
    (r"cash", "Dinheiro"),
]

_MESES = (
    "janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro"
)

_RE_ASPAS = re.compile(r"[\"“”](.+?)[\"“”]")
_RE_DATA_RELATIVA = re.compile(r"\b(hoje|ontem|anteontem)\b", re.IGNORECASE)
_RE_DATA_BARRA = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?(?![\d/])")
_RE_DATA_EXTENSO = re.compile(
    rf"\b\d{{1,2}}\s+de\s+(?:{_MESES})(?:\s+de\s+\d{{4}})?\b", re.IGNORECASE
)
_RE_DATA_DIA = re.compile(r"\bdia\s+(\d{1,2})\b", re.IGNORECASE)
_RE_VALOR = re.compile(
    r"(?<![\w/.,$])(?:r\$\s*)?"
    r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"(?![\w/]|[.,]\d)"
    r"(?:\s*(?:reais|real|conto|contos)\b)?",
    re.IGNORECASE,
)

_STOPWORDS = {
    "gastei", "gasto", "paguei", "comprei", "reais", "real",
    "no", "na", "nos", "nas", "com", "em", "de", "do", "da", "o", "a", "os", "as",
    "pelo", "pela", "por", "pra", "para", "um", "uma", "e", "via", "r$",
}  # fmt: skip


@dataclass
class DespesaParcial:
    valor: Decimal | None = None
    forma_pagamento: str | None = None
    data: date | None = None  # None só quando a data informada é inválida
    descricao: str | None = None


def _remover(texto: str, match: re.Match) -> str:
    return texto[: match.start()] + " " + texto[match.end() :]


def _data_segura(ano: int, mes: int, dia: int) -> date | None:
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _extrair_data(texto: str, hoje: date) -> tuple[str, date | None]:
    if m := _RE_DATA_RELATIVA.search(texto):
        dias = {"hoje": 0, "ontem": 1, "anteontem": 2}[m.group(1).lower()]
        return _remover(texto, m), hoje - timedelta(days=dias)

    if m := _RE_DATA_BARRA.search(texto):
        dia, mes, ano = int(m.group(1)), int(m.group(2)), m.group(3)
        if ano is None:
            data = _data_segura(hoje.year, mes, dia)
            if data is not None and data > hoje:  # sem ano: prefere o passado
                data = _data_segura(hoje.year - 1, mes, dia)
        else:
            data = _data_segura(int(ano) + (2000 if len(ano) == 2 else 0), mes, dia)
        return _remover(texto, m), data

    if m := _RE_DATA_EXTENSO.search(texto):
        base = datetime.combine(hoje, datetime.min.time())
        resultado = dateparser.parse(
            m.group(0),
            languages=["pt"],
            settings={"PREFER_DATES_FROM": "past", "RELATIVE_BASE": base},
        )
        return _remover(texto, m), resultado.date() if resultado else None

    if m := _RE_DATA_DIA.search(texto):
        dia = int(m.group(1))
        data = _data_segura(hoje.year, hoje.month, dia)
        if data is not None and data > hoje:  # "dia 28" no dia 5 → mês passado
            mes_anterior = hoje.replace(day=1) - timedelta(days=1)
            data = _data_segura(mes_anterior.year, mes_anterior.month, dia)
        return _remover(texto, m), data

    return texto, hoje


def parse_data(texto: str, hoje: date) -> date | None:
    """Data de uma resposta avulsa ("ontem", "05/09"...); None se não reconhecida/inválida."""
    restante, data = _extrair_data(texto, hoje)
    return data if restante != texto else None


def parse_valor(texto: str) -> Decimal | None:
    """Converte '45', '45,90', '45.90', '1.234,56' ou 'R$ 10' em Decimal (> 0)."""
    m = _RE_VALOR.search(texto)
    return _converter_valor(m.group(1)) if m else None


def _converter_valor(bruto: str) -> Decimal | None:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", bruto):
        bruto = bruto.replace(".", "")
    try:
        valor = Decimal(bruto.replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    if valor <= 0 or valor > VALOR_MAXIMO:
        return None
    return valor


def _extrair_valor(texto: str) -> tuple[str, Decimal | None]:
    m = _RE_VALOR.search(texto)
    if m is None:
        return texto, None
    return _remover(texto, m), _converter_valor(m.group(1))


def parse_forma_pagamento(texto: str) -> str | None:
    return _extrair_forma(texto)[1]


def _extrair_forma(texto: str) -> tuple[str, str | None]:
    for padrao, forma in _SINONIMOS_PAGAMENTO:
        if m := re.search(rf"\b{padrao}\b", texto, re.IGNORECASE):
            return _remover(texto, m), forma
    return texto, None


def limpar_descricao(texto: str) -> str | None:
    """Colapsa espaços e remove stopwords das pontas ("no mercado com" → "mercado")."""
    palavras = [p.strip(",.;:!?-") for p in texto.split()]
    palavras = [p for p in palavras if p]
    while palavras and palavras[0].lower() in _STOPWORDS:
        palavras.pop(0)
    while palavras and palavras[-1].lower() in _STOPWORDS:
        palavras.pop()
    if not palavras:
        return None
    descricao = " ".join(palavras)
    return descricao[0].upper() + descricao[1:]


def parse(texto: str, hoje: date) -> DespesaParcial:
    descricao_aspas = None
    if m := _RE_ASPAS.search(texto):
        descricao_aspas = m.group(1).strip() or None
        texto = _remover(texto, m)

    texto, data = _extrair_data(texto, hoje)
    texto, valor = _extrair_valor(texto)
    texto, forma = _extrair_forma(texto)

    descricao = limpar_descricao(descricao_aspas or texto)
    return DespesaParcial(valor=valor, forma_pagamento=forma, data=data, descricao=descricao)
