"""Execução local via polling: `python -m bot.main`."""

import asyncio

import structlog

from bot.app import ALLOWED_UPDATES, configurar_logging, criar_bot, criar_dispatcher
from bot.config import get_settings
from bot.db import criar_engine, criar_sessionmaker, garantir_diretorio_sqlite
from bot.handlers.start_ajuda import COMANDOS

log = structlog.get_logger()


async def main() -> None:
    settings = get_settings()
    configurar_logging(settings.log_level)
    garantir_diretorio_sqlite(settings.database_url)

    engine = criar_engine(settings.database_url)
    bot = criar_bot(settings)
    dp = criar_dispatcher(settings, criar_sessionmaker(engine))

    try:
        # Polling e webhook são exclusivos: não derruba a produção sem querer
        webhook = await bot.get_webhook_info()
        if webhook.url:
            log.error(
                "webhook_ativo",
                url=webhook.url,
                dica="use um bot de testes ou rode `python scripts/webhook.py remover`",
            )
            return
        await bot.set_my_commands(COMANDOS)
        log.info("bot_iniciado", modo="polling")
        await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
