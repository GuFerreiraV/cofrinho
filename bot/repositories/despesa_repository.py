from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Despesa

CENTAVOS = Decimal("0.01")


class DespesaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def criar(
        self,
        *,
        user_id: int,
        valor: Decimal,
        forma_pagamento: str,
        data: date,
        descricao: str,
        categoria: str,
    ) -> Despesa:
        despesa = Despesa(
            user_id=user_id,
            valor=valor,
            forma_pagamento=forma_pagamento,
            data=data,
            descricao=descricao,
            categoria=categoria,
        )
        self.session.add(despesa)
        await self.session.commit()
        await self.session.refresh(despesa)
        return despesa

    async def obter(self, despesa_id: int, user_id: int) -> Despesa | None:
        stmt = select(Despesa).where(Despesa.id == despesa_id, Despesa.user_id == user_id)
        return await self.session.scalar(stmt)

    async def atualizar_categoria(
        self, despesa_id: int, user_id: int, categoria: str
    ) -> Despesa | None:
        despesa = await self.obter(despesa_id, user_id)
        if despesa is None:
            return None
        despesa.categoria = categoria
        await self.session.commit()
        return despesa

    async def totais_por_categoria(
        self, user_id: int, inicio: date | None = None, fim: date | None = None
    ) -> dict[str, Decimal]:
        stmt = (
            select(Despesa.categoria, func.sum(Despesa.valor))
            .where(Despesa.user_id == user_id)
            .group_by(Despesa.categoria)
        )
        if inicio is not None:
            stmt = stmt.where(Despesa.data >= inicio)
        if fim is not None:
            stmt = stmt.where(Despesa.data <= fim)
        resultado = await self.session.execute(stmt)
        # SQLite devolve SUM como float: normaliza para Decimal com 2 casas
        return {
            categoria: Decimal(str(total)).quantize(CENTAVOS)
            for categoria, total in resultado.all()
        }
