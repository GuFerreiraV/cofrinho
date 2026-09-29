import asyncio
import hashlib
import hmac
import importlib.util
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.config import Settings
from bot.models import Base
from bot.repositories.despesa_repository import DespesaRepository
from bot.services.dashboard_service import DashboardService
from bot.web.auth import url_dashboard, usuario_do_dashboard, validar_init_data

TOKEN = "123:abc"
HOJE = date(2026, 9, 29)
AGORA = datetime(2026, 9, 29, 12, tzinfo=UTC)
DONO, OUTRO = 42, 99


def assinar(user_id: int, auth_date: datetime, token: str = TOKEN) -> str:
    """initData assinado como o Telegram faz (core.telegram.org/bots/webapps)."""
    campos = {
        "auth_date": str(int(auth_date.timestamp())),
        "query_id": "AAH",
        "user": json.dumps({"id": user_id, "first_name": "T"}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(campos.items()))
    secreto = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    campos["hash"] = hmac.new(secreto, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(campos)


GASTOS = [
    # (user, valor, data, categoria, forma, descricao)
    (DONO, "119.00", date(2026, 9, 28), "Comida", "Débito", "Mercado"),
    (DONO, "20.00", date(2026, 9, 29), "Comida", "Voucher", "Padaria"),
    (DONO, "60.00", date(2026, 9, 10), "Lazer", "Crédito", "Cinema"),
    (DONO, "300.00", date(2026, 8, 5), "Estudos", "Pix", "Curso"),
    (DONO, "50.00", date(2026, 3, 1), "Comida", "Pix", "Feira"),  # fora dos 6 meses
    (DONO, "999.00", date(2026, 10, 5), "Lazer", "Pix", "Futuro"),  # depois de hoje
    (OUTRO, "5000.00", date(2026, 9, 20), "Comida", "Pix", "De outro usuário"),
]


async def popular(repo: DespesaRepository) -> None:
    for user, valor, dia, categoria, forma, descricao in GASTOS:
        await repo.criar(
            user_id=user,
            valor=Decimal(valor),
            forma_pagamento=forma,
            data=dia,
            descricao=descricao,
            categoria=categoria,
        )


# ---------------------------------------------------------------- service


@pytest.fixture
async def servico(repo):
    await popular(repo)
    return DashboardService(repo, HOJE)


async def test_mes_atual_por_categoria(servico):
    r = await servico.resumo(DONO, "mes")
    assert r["periodo"] == {"chave": "mes", "rotulo": "Setembro/2026"}
    assert r["total_fmt"] == "R$ 199,00"
    assert r["quantidade"] == 3
    pizza = {i["rotulo"]: i["valor"] for i in r["pizza"]["itens"]}
    assert pizza == {"Comida": 139.0, "Lazer": 60.0}


async def test_cor_da_fatia_segue_a_categoria(servico):
    """O slot de cor é a posição fixa da categoria, não o ranking no período."""
    r = await servico.resumo(DONO, "3m")
    slots = {i["rotulo"]: i["slot"] for i in r["pizza"]["itens"]}
    assert slots == {"Lazer": 0, "Estudos": 1, "Comida": 2}


async def test_filtro_de_categoria_divide_por_forma_de_pagamento(servico):
    r = await servico.resumo(DONO, "mes", "Comida")
    assert r["pizza"]["titulo"] == "Por forma de pagamento"
    pizza = {i["rotulo"]: i["valor"] for i in r["pizza"]["itens"]}
    assert pizza == {"Débito": 119.0, "Voucher": 20.0}
    assert r["total_fmt"] == "R$ 139,00"


async def test_barras_ultimos_6_meses(servico):
    r = await servico.resumo(DONO, "mes")
    itens = r["barras"]["itens"]
    assert [i["rotulo"] for i in itens] == [
        "Abr/26",
        "Mai/26",
        "Jun/26",
        "Jul/26",
        "Ago/26",
        "Set/26",
    ]
    assert [i["valor"] for i in itens] == [0, 0, 0, 0, 300.0, 199.0]


async def test_barras_respeitam_a_categoria(servico):
    r = await servico.resumo(DONO, "mes", "Estudos")
    assert [i["valor"] for i in r["barras"]["itens"]][-2:] == [300.0, 0]


async def test_maiores_gastos(servico):
    r = await servico.resumo(DONO, "tudo")
    assert [m["descricao"] for m in r["maiores"]] == [
        "Curso",
        "Mercado",
        "Cinema",
        "Feira",
        "Padaria",
    ]
    assert r["maiores"][0]["valor_fmt"] == "R$ 300,00"


async def test_isolamento_entre_usuarios(servico):
    r = await servico.resumo(OUTRO, "tudo")
    assert r["total_fmt"] == "R$ 5.000,00"
    assert [m["descricao"] for m in r["maiores"]] == ["De outro usuário"]


async def test_filtros_invalidos(servico):
    with pytest.raises(ValueError):
        await servico.resumo(DONO, "ano")
    with pytest.raises(ValueError):
        await servico.resumo(DONO, "mes", "Viagens")


async def test_sem_gastos(repo):
    r = await DashboardService(repo, HOJE).resumo(DONO, "mes")
    assert r["quantidade"] == 0 and r["pizza"]["itens"] == [] and r["maiores"] == []


# ---------------------------------------------------------------- autenticação


def test_init_data_valido():
    assert validar_init_data(assinar(DONO, AGORA), TOKEN, AGORA) == DONO


def test_init_data_de_outro_bot_e_recusado():
    assert validar_init_data(assinar(DONO, AGORA, token="999:outro"), TOKEN, AGORA) is None


def test_init_data_adulterado_e_recusado():
    adulterado = assinar(DONO, AGORA).replace("%22id%22%3A+42", "%22id%22%3A+99")
    assert adulterado != assinar(DONO, AGORA)
    assert validar_init_data(adulterado, TOKEN, AGORA) is None


def test_init_data_expirado_e_recusado():
    antigo = assinar(DONO, AGORA - timedelta(hours=25))
    assert validar_init_data(antigo, TOKEN, AGORA) is None


def test_init_data_lixo_e_recusado():
    assert validar_init_data("nada=aqui", TOKEN, AGORA) is None
    assert validar_init_data("%%%", TOKEN, AGORA) is None


def test_atalho_de_desenvolvimento_so_fora_da_vercel():
    s = Settings(_env_file=None, bot_token=TOKEN, dashboard_dev_user_id=7)
    assert usuario_do_dashboard("", s, AGORA, ambiente={}) == 7
    assert usuario_do_dashboard("", s, AGORA, ambiente={"VERCEL": "1"}) is None
    sem_atalho = Settings(_env_file=None, bot_token=TOKEN)
    assert usuario_do_dashboard("", sem_atalho, AGORA, ambiente={}) is None


def test_init_data_valido_vence_o_atalho():
    s = Settings(_env_file=None, bot_token=TOKEN, dashboard_dev_user_id=7)
    assert usuario_do_dashboard(assinar(DONO, AGORA), s, AGORA, ambiente={}) == DONO


def test_url_do_dashboard():
    s = Settings(_env_file=None, bot_token=TOKEN)
    assert url_dashboard(s, {}) is None
    assert (
        url_dashboard(s, {"VERCEL_PROJECT_PRODUCTION_URL": "bot.vercel.app"})
        == "https://bot.vercel.app/api/dashboard"
    )
    s = Settings(_env_file=None, bot_token=TOKEN, dashboard_url="https://meu.dominio/api/dashboard")
    assert url_dashboard(s, {"VERCEL_PROJECT_PRODUCTION_URL": "x"}) == s.dashboard_url


# ---------------------------------------------------------------- endpoint


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    url = f"sqlite+aiosqlite:///{tmp_path_factory.mktemp('dash')}/t.db"

    async def preparar():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as s:
            await popular(DespesaRepository(s))
        await engine.dispose()

    asyncio.run(preparar())
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BOT_TOKEN", TOKEN)
        mp.setenv("DATABASE_URL", url)
        mp.chdir(tmp_path_factory.mktemp("sem_env"))  # não lê o .env do desenvolvedor
        caminho = Path(__file__).resolve().parent.parent / "api" / "dashboard.py"
        spec = importlib.util.spec_from_file_location("api_dashboard", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    with TestClient(modulo.app) as c:
        yield c


def test_get_devolve_a_pagina(cliente):
    r = cliente.get("/api/dashboard")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "telegram-web-app.js" in r.text


def test_post_sem_init_data_e_401(cliente):
    assert cliente.post("/api/dashboard", json={"periodo": "mes"}).status_code == 401


def test_post_com_init_data_valido(cliente):
    init = assinar(DONO, datetime.now(UTC))
    r = cliente.post("/api/dashboard", json={"initData": init, "periodo": "tudo"})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    dados = r.json()
    assert "De outro usuário" not in [m["descricao"] for m in dados["maiores"]]


def test_post_nao_aceita_user_id_do_cliente(cliente):
    """O usuário vem só do initData assinado: um campo extra não muda nada."""
    init = assinar(DONO, datetime.now(UTC))
    r = cliente.post("/api/dashboard", json={"initData": init, "periodo": "tudo", "user_id": OUTRO})
    assert "De outro usuário" not in [m["descricao"] for m in r.json()["maiores"]]


def test_post_com_filtro_invalido(cliente):
    init = assinar(DONO, datetime.now(UTC))
    r = cliente.post("/api/dashboard", json={"initData": init, "categoria": "Viagens"})
    assert r.status_code == 422
    r = cliente.post("/api/dashboard", json={"initData": init, "periodo": "ano"})
    assert r.status_code == 422
