from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Parâmetros da URL no formato libpq (usados pelo Neon) que o asyncpg não aceita
_PARAMS_LIBPQ = ("sslmode", "channel_binding")


def preparar_url(database_url: str) -> tuple[URL, dict[str, Any]]:
    """Normaliza a URL e devolve os `connect_args` do driver.

    Aceita a string de conexão do Neon como vem do painel
    (`postgresql://...?sslmode=require&channel_binding=require`) e a converte
    para o driver `asyncpg`, que usa `ssl` em vez de `sslmode`.
    """
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        return url, {}

    sslmode = url.query.get("sslmode")
    url = url.set(drivername="postgresql+asyncpg").difference_update_query(_PARAMS_LIBPQ)
    connect_args: dict[str, Any] = {
        # O pooler do Neon (PgBouncer em modo transação) não mantém prepared
        # statements entre transações: desliga o cache e usa nomes únicos
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }
    if sslmode and sslmode != "disable":
        connect_args["ssl"] = "require"
    return url, connect_args


def criar_engine(database_url: str) -> AsyncEngine:
    url, connect_args = preparar_url(database_url)
    if url.get_backend_name() == "postgresql":
        # Serverless: sem pool entre invocações (cada request abre e fecha a conexão;
        # o pooling fica a cargo do pooler do Neon)
        return create_async_engine(url, connect_args=connect_args, poolclass=NullPool)
    return create_async_engine(url)


def criar_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


def garantir_diretorio_sqlite(database_url: str) -> None:
    """Cria a pasta do arquivo SQLite (ex: data/) se ainda não existir."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
