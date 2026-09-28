from datetime import date, timedelta
from decimal import Decimal

from bot.repositories.despesa_repository import DespesaRepository
from bot.services.formatador_service import formatar_data, nome_mes

Relatorio = tuple[str, dict[str, Decimal]]


class RelatorioService:
    """Agrega gastos por período. Independente do aiogram (reuso no dashboard)."""

    def __init__(self, repositorio: DespesaRepository, hoje: date) -> None:
        self.repositorio = repositorio
        self.hoje = hoje

    async def diario(self, user_id: int) -> Relatorio:
        totais = await self.repositorio.totais_por_categoria(user_id, self.hoje, self.hoje)
        return f"📅 Resumo de hoje ({formatar_data(self.hoje)})", totais

    async def semanal(self, user_id: int) -> Relatorio:
        inicio = self.hoje - timedelta(days=self.hoje.weekday())  # segunda-feira
        totais = await self.repositorio.totais_por_categoria(user_id, inicio, self.hoje)
        titulo = f"🗓️ Resumo da semana ({inicio:%d/%m} a {self.hoje:%d/%m/%Y})"
        return titulo, totais

    async def mensal(self, user_id: int) -> Relatorio:
        inicio = self.hoje.replace(day=1)
        totais = await self.repositorio.totais_por_categoria(user_id, inicio, self.hoje)
        return f"📊 Resumo de {nome_mes(self.hoje)}", totais

    async def geral(self, user_id: int) -> Relatorio:
        totais = await self.repositorio.totais_por_categoria(user_id)
        return "🏦 Resumo geral (todo o histórico)", totais
