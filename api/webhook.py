"""Endpoint do webhook do Telegram (função serverless da Vercel): POST /api/webhook."""

import sys
from pathlib import Path
from secrets import compare_digest

# Garante que o pacote `bot` (na raiz do projeto) seja importável na Vercel
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog  # noqa: E402
from aiogram.types import Update  # noqa: E402
from fastapi import FastAPI, Header, Request, Response  # noqa: E402

from bot.app import configurar_logging, criar_bot, criar_dispatcher  # noqa: E402
from bot.config import get_settings  # noqa: E402
from bot.db import criar_engine, criar_sessionmaker  # noqa: E402

settings = get_settings()
configurar_logging(settings.log_level)
log = structlog.get_logger()

# Criados uma vez por instância e reaproveitados enquanto ela estiver "quente"
engine = criar_engine(settings.database_url.get_secret_value())
dp = criar_dispatcher(settings, criar_sessionmaker(engine))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _secret_valido(recebido: str | None) -> bool:
    esperado = settings.webhook_secret
    if esperado is None or recebido is None:
        return False
    return compare_digest(recebido, esperado.get_secret_value())


@app.post("/api/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    if not _secret_valido(x_telegram_bot_api_secret_token):
        return Response(status_code=401)

    # Processa o update inteiro antes de responder: a função é congelada após a resposta.
    # O Bot (sessão HTTP) é criado por request para não ficar preso a um event loop antigo.
    try:
        async with criar_bot(settings) as bot:
            update = Update.model_validate(await request.json(), context={"bot": bot})
            await dp.feed_update(bot, update)
    except Exception:
        # Sempre 200: com erro, o Telegram reenviaria o update (ex: gasto registrado em dobro)
        log.exception("erro_ao_processar_update")
    return Response(status_code=200)


@app.get("/api/webhook")
async def status() -> dict[str, str]:
    return {"status": "ok"}
