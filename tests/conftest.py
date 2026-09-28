import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.models import Base
from bot.repositories.despesa_repository import DespesaRepository


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
