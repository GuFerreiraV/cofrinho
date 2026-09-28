import pytest
from aiogram.fsm.storage.base import StorageKey
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.fsm_storage import SqlAlchemyStorage
from bot.models import FsmEstado
from bot.states.registro_gasto import RegistroGasto

CHAVE = StorageKey(bot_id=1, chat_id=42, user_id=42)
OUTRA_CHAVE = StorageKey(bot_id=1, chat_id=7, user_id=7)


@pytest.fixture
def storage(session):
    return SqlAlchemyStorage(async_sessionmaker(session.bind, expire_on_commit=False))


async def _linhas(session) -> int:
    return await session.scalar(select(func.count()).select_from(FsmEstado))


async def test_estado_e_dados_vazios_por_padrao(storage):
    assert await storage.get_state(CHAVE) is None
    assert await storage.get_data(CHAVE) == {}


async def test_salva_e_le_estado_e_dados(storage):
    await storage.set_state(CHAVE, RegistroGasto.aguardando_forma)
    await storage.set_data(CHAVE, {"valor": "45.00", "descricao": "Mercado"})
    assert await storage.get_state(CHAVE) == RegistroGasto.aguardando_forma.state
    assert await storage.get_data(CHAVE) == {"valor": "45.00", "descricao": "Mercado"}


async def test_update_data_mescla(storage):
    await storage.set_data(CHAVE, {"valor": "45.00"})
    await storage.update_data(CHAVE, {"forma": "Pix"})
    assert await storage.get_data(CHAVE) == {"valor": "45.00", "forma": "Pix"}


async def test_chaves_isoladas(storage):
    await storage.set_state(CHAVE, "a")
    assert await storage.get_state(OUTRA_CHAVE) is None


async def test_limpar_remove_a_linha(storage, session):
    await storage.set_state(CHAVE, RegistroGasto.aguardando_valor)
    await storage.set_data(CHAVE, {"valor": None})
    assert await _linhas(session) == 1
    # Equivalente a state.clear()
    await storage.set_state(CHAVE, None)
    await storage.set_data(CHAVE, {})
    assert await _linhas(session) == 0
    assert await storage.get_state(CHAVE) is None


async def test_limpar_chave_inexistente_nao_cria_linha(storage, session):
    await storage.set_state(CHAVE, None)
    await storage.set_data(CHAVE, {})
    assert await _linhas(session) == 0
