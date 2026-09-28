from collections.abc import Mapping
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder, StateType, StorageKey
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.models import FsmEstado


class SqlAlchemyStorage(BaseStorage):
    """Storage do FSM do aiogram numa tabela do banco.

    Em serverless cada update pode cair numa instância nova, então o estado da
    conversa ("bot pergunta o que falta") não pode ficar em memória.
    """

    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self.sessionmaker = sessionmaker
        self.key_builder = DefaultKeyBuilder(with_bot_id=True, with_destiny=True)

    async def _obter(self, key: StorageKey) -> FsmEstado | None:
        async with self.sessionmaker() as session:
            return await session.get(FsmEstado, self.key_builder.build(key))

    async def _salvar(self, key: StorageKey, **campos: Any) -> None:
        chave = self.key_builder.build(key)
        async with self.sessionmaker() as session:
            registro = await session.get(FsmEstado, chave)
            if registro is None:
                registro = FsmEstado(chave=chave, estado=None, dados={})
                session.add(registro)
            for campo, valor in campos.items():
                setattr(registro, campo, valor)
            if registro.estado is None and not registro.dados:
                # Conversa encerrada: remove a linha em vez de guardar um registro vazio
                if registro in session.new:
                    session.expunge(registro)
                else:
                    await session.delete(registro)
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
