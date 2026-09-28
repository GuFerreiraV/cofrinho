import ssl

from bot.db import preparar_url


def test_url_do_neon_vira_asyncpg_com_ssl():
    url, args = preparar_url(
        "postgresql://u:s@ep-x-pooler.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert url.drivername == "postgresql+asyncpg"
    assert "sslmode" not in url.query and "channel_binding" not in url.query
    assert url.password == "s"
    contexto = args["ssl"]
    assert isinstance(contexto, ssl.SSLContext)
    assert contexto.verify_mode == ssl.CERT_REQUIRED
    assert contexto.check_hostname
    assert args["statement_cache_size"] == 0


def test_postgres_sem_ssl():
    url, args = preparar_url("postgresql://u:s@localhost/db")
    assert url.drivername == "postgresql+asyncpg"
    assert "ssl" not in args


def test_sqlite_nao_muda():
    url, args = preparar_url("sqlite+aiosqlite:///./data/financeiro.db")
    assert url.drivername == "sqlite+aiosqlite"
    assert args == {}
