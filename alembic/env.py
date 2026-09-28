import asyncio
from logging.config import fileConfig

from alembic import context
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import Connection

from bot.db import criar_engine, garantir_diretorio_sqlite, preparar_url
from bot.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


class _DbSettings(BaseSettings):
    """Só a URL do banco: migrations não devem exigir BOT_TOKEN."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    database_url: SecretStr = SecretStr("sqlite+aiosqlite:///./data/financeiro.db")


# Não usa config.set_main_option: senhas com "%" quebram a interpolação do configparser
database_url = _DbSettings().database_url.get_secret_value()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=preparar_url(database_url)[0],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    garantir_diretorio_sqlite(database_url)
    engine = criar_engine(database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
