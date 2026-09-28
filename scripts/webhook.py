"""Gerencia o webhook do bot no Telegram.

    python scripts/webhook.py registrar   # aponta o Telegram para WEBHOOK_URL (produção)
    python scripts/webhook.py remover     # desliga o webhook (volta a permitir polling local)
    python scripts/webhook.py info        # mostra o status atual

Lê BOT_TOKEN, WEBHOOK_URL e WEBHOOK_SECRET do .env (ou do ambiente).
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.app import ALLOWED_UPDATES, criar_bot  # noqa: E402
from bot.config import get_settings  # noqa: E402
from bot.handlers.start_ajuda import COMANDOS  # noqa: E402


async def registrar() -> None:
    settings = get_settings()
    if not settings.webhook_url or settings.webhook_secret is None:
        sys.exit("❌ Defina WEBHOOK_URL e WEBHOOK_SECRET no .env")
    async with criar_bot(settings) as bot:
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.webhook_secret.get_secret_value(),
            allowed_updates=ALLOWED_UPDATES,
        )
        await bot.set_my_commands(COMANDOS)
    print(f"✅ Webhook registrado: {settings.webhook_url}")
    await info()


async def remover() -> None:
    async with criar_bot(get_settings()) as bot:
        await bot.delete_webhook()
    print("✅ Webhook removido. O polling local (python -m bot.main) já pode ser usado.")


async def info() -> None:
    async with criar_bot(get_settings()) as bot:
        w = await bot.get_webhook_info()
    print(f"URL:                 {w.url or '(nenhuma: modo polling)'}")
    print(f"Updates pendentes:   {w.pending_update_count}")
    if w.last_error_message:
        print(f"Último erro:         {w.last_error_date} — {w.last_error_message}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("acao", choices=["registrar", "remover", "info"])
    acao = parser.parse_args().acao
    asyncio.run({"registrar": registrar, "remover": remover, "info": info}[acao]())


if __name__ == "__main__":
    main()
