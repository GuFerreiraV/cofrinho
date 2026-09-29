"""Dados do dashboard. Agrega em Python (mesmo resultado no SQLite e no PostgreSQL;
o volume de um controle de gastos pessoal é pequeno)."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from bot.models import Despesa
from bot.repositories.despesa_repository import DespesaRepository
from bot.services.categorizacao_service import CATEGORIAS, icone
from bot.services.formatador_service import ICONES_PAGAMENTO, MESES, formatar_brl, nome_mes
from bot.services.parser_service import FORMAS_PAGAMENTO

Periodo = Literal["mes", "3m", "tudo"]
PERIODOS: tuple[Periodo, ...] = ("mes", "3m", "tudo")
MESES_BARRAS = 6
TOP_MAIORES = 5


def _voltar_meses(dia: date, meses: int) -> date:
    """Primeiro dia do mês `meses` antes do mês de `dia`."""
    indice = dia.year * 12 + (dia.month - 1) - meses
    return date(indice // 12, indice % 12 + 1, 1)


def _item(rotulo: str, icone_: str, valor: Decimal) -> dict[str, Any]:
    return {
        "rotulo": rotulo,
        "icone": icone_,
        "valor": float(valor),
        "valor_fmt": formatar_brl(valor),
    }


class DashboardService:
    def __init__(self, repositorio: DespesaRepository, hoje: date) -> None:
        self.repositorio = repositorio
        self.hoje = hoje

    def _intervalo(self, periodo: Periodo) -> tuple[date | None, str]:
        if periodo == "mes":
            return self.hoje.replace(day=1), nome_mes(self.hoje)
        if periodo == "3m":
            return _voltar_meses(self.hoje, 2), "Últimos 3 meses"
        return None, "Todo o período"

    async def resumo(
        self, user_id: int, periodo: Periodo = "mes", categoria: str | None = None
    ) -> dict[str, Any]:
        if periodo not in PERIODOS:
            raise ValueError(f"período inválido: {periodo}")
        if categoria is not None and categoria not in CATEGORIAS:
            raise ValueError(f"categoria inválida: {categoria}")

        inicio, rotulo_periodo = self._intervalo(periodo)
        despesas = await self.repositorio.listar(user_id, inicio, self.hoje, categoria)
        total = sum((d.valor for d in despesas), Decimal("0"))

        return {
            "periodo": {"chave": periodo, "rotulo": rotulo_periodo},
            "categoria": categoria,
            "total": float(total),
            "total_fmt": formatar_brl(total),
            "quantidade": len(despesas),
            "pizza": self._pizza(despesas, categoria),
            "barras": await self._barras(user_id, categoria),
            "maiores": self._maiores(despesas),
        }

    def _pizza(self, despesas: list[Despesa], categoria: str | None) -> dict[str, Any]:
        """Por categoria; com uma categoria filtrada, por forma de pagamento.

        A ordem das fatias é fixa (a das categorias/formas), para que cada uma
        mantenha a mesma cor em qualquer filtro."""
        somas: dict[str, Decimal] = defaultdict(Decimal)
        if categoria is None:
            for d in despesas:
                somas[d.categoria] += d.valor
            ordem, icones, titulo = list(CATEGORIAS), CATEGORIAS, "Por categoria"
        else:
            for d in despesas:
                somas[d.forma_pagamento] += d.valor
            ordem, icones = list(FORMAS_PAGAMENTO), ICONES_PAGAMENTO
            titulo = "Por forma de pagamento"
        ordem += sorted(chave for chave in somas if chave not in ordem)  # valores legados
        itens = [
            {**_item(chave, icones.get(chave, "📦"), somas[chave]), "slot": posicao}
            for posicao, chave in enumerate(ordem)
            if somas.get(chave)
        ]
        return {"titulo": titulo, "itens": itens}

    async def _barras(self, user_id: int, categoria: str | None) -> dict[str, Any]:
        """Total por mês nos últimos MESES_BARRAS meses (inclui o atual)."""
        inicio = _voltar_meses(self.hoje, MESES_BARRAS - 1)
        despesas = await self.repositorio.listar(user_id, inicio, self.hoje, categoria)
        somas: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        for d in despesas:
            somas[(d.data.year, d.data.month)] += d.valor
        itens = []
        for n in range(MESES_BARRAS - 1, -1, -1):
            mes = _voltar_meses(self.hoje, n)
            rotulo = f"{MESES[mes.month - 1][:3]}/{mes.year % 100:02d}"
            itens.append(_item(rotulo, "", somas[(mes.year, mes.month)]))
        return {"titulo": f"Últimos {MESES_BARRAS} meses", "itens": itens}

    def _maiores(self, despesas: list[Despesa]) -> list[dict[str, Any]]:
        maiores = sorted(despesas, key=lambda d: (d.valor, d.data), reverse=True)[:TOP_MAIORES]
        return [
            {
                "data": d.data.strftime("%d/%m/%Y"),
                "descricao": d.descricao,
                "categoria": d.categoria,
                "icone": icone(d.categoria),
                "forma_pagamento": d.forma_pagamento,
                "valor": float(d.valor),
                "valor_fmt": formatar_brl(d.valor),
            }
            for d in maiores
        ]
