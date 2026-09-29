"""Autenticação do dashboard (Mini App do Telegram).

O Telegram entrega ao Mini App um `initData` assinado com o token do bot. O
usuário é identificado **só** por esse dado validado, nunca por um id enviado
pelo cliente.
"""

import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from aiogram.utils.web_app import safe_parse_webapp_init_data

from bot.config import Settings

VALIDADE_INIT_DATA = timedelta(hours=24)


def validar_init_data(init_data: str, bot_token: str, agora: datetime) -> int | None:
    """Id do usuário se o initData tiver assinatura válida e não estiver expirado."""
    try:
        dados = safe_parse_webapp_init_data(bot_token, init_data)
    except ValueError:
        return None
    auth_date = dados.auth_date
    if auth_date.tzinfo is None:
        auth_date = auth_date.replace(tzinfo=UTC)
    if agora - auth_date > VALIDADE_INIT_DATA or dados.user is None:
        return None
    return dados.user.id


def usuario_do_dashboard(
    init_data: str,
    settings: Settings,
    agora: datetime | None = None,
    ambiente: Mapping[str, str] = os.environ,
) -> int | None:
    agora = agora or datetime.now(UTC)
    # Atalho de desenvolvimento: nunca vale na Vercel (que sempre define VERCEL)
    if not init_data and settings.dashboard_dev_user_id is not None and "VERCEL" not in ambiente:
        return settings.dashboard_dev_user_id
    if not init_data:
        return None
    return validar_init_data(init_data, settings.bot_token.get_secret_value(), agora)


def url_dashboard(settings: Settings, ambiente: Mapping[str, str] = os.environ) -> str | None:
    """URL pública do Mini App (precisa ser HTTPS), ou None se não houver."""
    if settings.dashboard_url:
        return settings.dashboard_url
    # Variável de sistema injetada pela Vercel: domínio de produção, sem https://
    if dominio := ambiente.get("VERCEL_PROJECT_PRODUCTION_URL"):
        return f"https://{dominio}/api/dashboard"
    return None
