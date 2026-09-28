"""Montagem do bot, compartilhada entre o polling local (bot/main.py) e o webhook (api/)."""

import logging
import sys

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import Settings
from bot.fsm_storage import SqlAlchemyStorage
from bot.handlers import gasto, relatorios, start_ajuda
from bot.middlewares import DbSessionMiddleware

ALLOWED_UPDATES = ["message", "callback_query"]


def configurar_logging(nivel: str) -> None:
    nivel = nivel.upper()
    logging.basicConfig(level=nivel, format="%(message)s")
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(nivel)),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            # Sem cores fora do terminal (ex: logs da Vercel)
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
    )


def criar_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def criar_dispatcher(settings: Settings, sessionmaker: async_sessionmaker) -> Dispatcher:
    dp = Dispatcher(storage=SqlAlchemyStorage(sessionmaker), settings=settings)
    dp.update.middleware(DbSessionMiddleware(sessionmaker))
    # Ordem importa: comandos antes do catch-all de texto livre (em gasto.router)
    dp.include_routers(start_ajuda.router, relatorios.router, gasto.router)
    return dp
