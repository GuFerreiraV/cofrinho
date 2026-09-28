from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder, StateType, StorageKey
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.models import FsmEstado

# Conversa parada há mais tempo que isso é descartada: o usuário recomeça do zero
EXPIRACAO = timedelta(hours=24)


def _expirado(registro: FsmEstado, agora: datetime) -> bool:
    atualizado = registro.atualizado_em
    if atualizado.tzinfo is None:  # SQLite devolve datetime sem fuso (gravado em UTC)
        atualizado = atualizado.replace(tzinfo=UTC)
    return agora - atualizado > EXPIRACAO


class SqlAlchemyStorage(BaseStorage):
    """Storage do FSM do aiogram numa tabela do banco.

    Em serverless cada update pode cair numa instância nova, então o estado da
    conversa ("bot pergunta o que falta") não pode ficar em memória.
    """

    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self.sessionmaker = sessionmaker
        self.key_builder = DefaultKeyBuilder(with_bot_id=True, with_destiny=True)

    async def _obter_valido(self, session: AsyncSession, chave: str) -> FsmEstado | None:
        """Busca o registro; se estiver expirado, apaga e responde como inexistente."""
        registro = await session.get(FsmEstado, chave)
        if registro is not None and _expirado(registro, datetime.now(UTC)):
            await session.delete(registro)
            await session.flush()
            return None
        return registro

    async def _obter(self, key: StorageKey) -> FsmEstado | None:
        async with self.sessionmaker() as session:
            registro = await self._obter_valido(session, self.key_builder.build(key))
            await session.commit()
            return registro

    async def _salvar(self, key: StorageKey, **campos: Any) -> None:
        chave = self.key_builder.build(key)
        async with self.sessionmaker() as session:
            registro = await self._obter_valido(session, chave)
            novo = registro is None
            if novo:
                registro = FsmEstado(chave=chave, estado=None, dados={})
            for campo, valor in campos.items():
                setattr(registro, campo, valor)

            vazio = registro.estado is None and not registro.dados
            if vazio and not novo:
                # Conversa encerrada: remove a linha em vez de guardar um registro vazio
                await session.delete(registro)
            elif not vazio and novo:
                # Aproveita o início de uma conversa para limpar as abandonadas (sem cron)
                limite = datetime.now(UTC) - EXPIRACAO
                await session.execute(delete(FsmEstado).where(FsmEstado.atualizado_em < limite))
                session.add(registro)
            await session.commit()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        estado = state.state if isinstance(state, State) else state
        await self._salvar(key, estado=estado)

    async def get_state(self, key: StorageKey) -> str | None:
        registro = await self._obter(key)
        return registro.estado if registro else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        await self._salvar(key, dados=dict(data))

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        registro = await self._obter(key)
        return dict(registro.dados) if registro and registro.dados else {}

    async def close(self) -> None:
        pass
