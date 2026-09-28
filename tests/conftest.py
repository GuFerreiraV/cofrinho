import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.models import Base
from bot.repositories.despesa_repository import DespesaRepository

WEBHOOK_SECRET = "segredo-de-teste"


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def repo(session):
    return DespesaRepository(session)


@pytest.fixture(scope="session")
def api_webhook(tmp_path_factory):
    """Módulo api/webhook.py carregado uma única vez.

    Os routers do aiogram só podem entrar em um Dispatcher, então todos os testes
    que precisam do Dispatcher real compartilham o criado por este módulo.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BOT_TOKEN", "123:abc")
        mp.setenv("WEBHOOK_SECRET", WEBHOOK_SECRET)
        mp.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path_factory.mktemp('db')}/t.db")
        caminho = Path(__file__).resolve().parent.parent / "api" / "webhook.py"
        spec = importlib.util.spec_from_file_location("api_webhook", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    return modulo
