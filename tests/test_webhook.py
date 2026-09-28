import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

SECRET = "segredo-de-teste"
UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 1790000000,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 42, "is_bot": False, "first_name": "T"},
        "text": "/ajuda",
    },
}


@pytest.fixture(scope="module")
def _modulo(tmp_path_factory):
    # Carregado uma vez: os routers do aiogram só podem entrar em um Dispatcher
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BOT_TOKEN", "123:abc")
        mp.setenv("WEBHOOK_SECRET", SECRET)
        mp.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path_factory.mktemp('db')}/t.db")
        caminho = Path(__file__).resolve().parent.parent / "api" / "webhook.py"
        spec = importlib.util.spec_from_file_location("api_webhook", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def webhook(_modulo, monkeypatch):
    # O dispatcher real não é chamado: só verificamos o que o endpoint repassa a ele
    monkeypatch.setattr(_modulo.dp, "feed_update", AsyncMock())
    return _modulo


def _post(modulo, secret):
    headers = {"X-Telegram-Bot-Api-Secret-Token": secret} if secret else {}
    return TestClient(modulo.app).post("/api/webhook", json=UPDATE, headers=headers)


def test_sem_secret_retorna_401(webhook):
    assert _post(webhook, None).status_code == 401
    webhook.dp.feed_update.assert_not_called()


def test_secret_errado_retorna_401(webhook):
    assert _post(webhook, "errado").status_code == 401
    webhook.dp.feed_update.assert_not_called()


def test_update_valido_e_processado(webhook):
    assert _post(webhook, SECRET).status_code == 200
    webhook.dp.feed_update.assert_awaited_once()
    update = webhook.dp.feed_update.await_args.args[1]
    assert update.message.text == "/ajuda"


def test_erro_no_handler_ainda_retorna_200(webhook):
    webhook.dp.feed_update.side_effect = RuntimeError("falhou")
    assert _post(webhook, SECRET).status_code == 200


def test_sem_webhook_secret_configurado_recusa_tudo(webhook, monkeypatch):
    monkeypatch.setattr(webhook.settings, "webhook_secret", None)
    assert _post(webhook, SECRET).status_code == 401


def test_healthcheck(webhook):
    assert TestClient(webhook.app).get("/api/webhook").json() == {"status": "ok"}
