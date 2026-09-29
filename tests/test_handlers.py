"""Fluxos do bot ponta a ponta: Dispatcher real, Telegram falso, SQLite em memória."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.middlewares import DbSessionMiddleware
from bot.models import Despesa
from bot.services.parser_service import MAX_TEXTO

BOT = User(id=123, is_bot=True, first_name="bot", username="bot")
DONO = User(id=42, is_bot=False, first_name="Dono")
INTRUSO = User(id=99, is_bot=False, first_name="Intruso")
GRUPO = Chat(id=-100123, type="group", title="Grupo")


def privado(usuario: User) -> Chat:
    return Chat(id=usuario.id, type="private")


class TelegramFalso(BaseSession):
    """Registra os métodos chamados em vez de enviá-los ao Telegram."""

    def __init__(self) -> None:
        super().__init__()
        self.chamadas: list[TelegramMethod] = []

    async def make_request(self, bot, method, timeout=None):
        self.chamadas.append(method)
        if method.__returning__ is Message:
            chat = Chat(id=getattr(method, "chat_id", 0) or 0, type="private")
            return Message(message_id=1, date=datetime.now(), chat=chat, from_user=BOT, text="")
        return True

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def close(self) -> None:
        pass

    def textos(self) -> list[str]:
        textos = [getattr(m, "text", None) for m in self.chamadas]
        return [t for t in textos if t]

    def alertas(self) -> list[str]:
        return [m.text for m in self.chamadas if isinstance(m, AnswerCallbackQuery) and m.text]


@pytest.fixture
def telegram():
    return TelegramFalso()


@pytest.fixture
def bot(telegram):
    return Bot("123:abc", session=telegram)


@pytest.fixture
def sessionmaker(session):
    return async_sessionmaker(session.bind, expire_on_commit=False)


@pytest.fixture
def dp(api_webhook, sessionmaker, monkeypatch):
    """Dispatcher real (compartilhado), apontado para o banco em memória deste teste."""
    dp = api_webhook.dp
    monkeypatch.setattr(dp.storage, "sessionmaker", sessionmaker)
    for middleware in dp.update.middleware:
        if isinstance(middleware, DbSessionMiddleware):
            monkeypatch.setattr(middleware, "sessionmaker", sessionmaker)
    return dp


_ids = iter(range(1, 10_000))


async def mensagem(dp, bot, texto: str, usuario: User = DONO, chat: Chat | None = None):
    n = next(_ids)
    msg = Message(
        message_id=n,
        date=datetime.now(),
        chat=chat or privado(usuario),
        from_user=usuario,
        text=texto,
    )
    await dp.feed_update(bot, Update(update_id=n, message=msg))


async def clique(dp, bot, data: str, usuario: User = DONO, chat: Chat | None = None):
    n = next(_ids)
    # A mensagem com os botões é do bot, não do usuário
    msg_do_bot = Message(
        message_id=n, date=datetime.now(), chat=chat or privado(usuario), from_user=BOT, text="x"
    )
    callback = CallbackQuery(
        id=str(n), from_user=usuario, chat_instance="c", message=msg_do_bot, data=data
    )
    await dp.feed_update(bot, Update(update_id=n, callback_query=callback))


async def despesas(session) -> list[Despesa]:
    return list(await session.scalars(select(Despesa).order_by(Despesa.id)))


async def _criar_despesa(repo, user_id=DONO.id):
    return await repo.criar(
        user_id=user_id,
        valor=Decimal("45"),
        forma_pagamento="Pix",
        data=date(2026, 9, 1),
        descricao="Mercado",
        categoria="Comida",
    )


# ---------------------------------------------------------------- fluxo normal


async def test_registro_direto(dp, bot, telegram, session):
    await mensagem(dp, bot, '/gasto 45 debito "mercado"')
    [despesa] = await despesas(session)
    assert despesa.user_id == DONO.id
    assert despesa.categoria == "Comida"
    assert "Gasto registrado" in telegram.textos()[-1]


async def test_registro_concluido_por_clique_usa_quem_clicou(dp, bot, session):
    await mensagem(dp, bot, "50 pix xpto")
    assert await despesas(session) == []  # aguardando a categoria
    await clique(dp, bot, "cat:Lazer")
    [despesa] = await despesas(session)
    assert despesa.user_id == DONO.id  # não o id do bot, autor da mensagem com os botões
    assert despesa.categoria == "Lazer"


async def test_relatorio_mostra_so_os_gastos_do_usuario(dp, bot, telegram, repo):
    await _criar_despesa(repo, user_id=DONO.id)
    await _criar_despesa(repo, user_id=INTRUSO.id)
    await mensagem(dp, bot, "/geral")
    assert "R$ 45,00" in telegram.textos()[-1]
    assert "R$ 90,00" not in telegram.textos()[-1]


# ---------------------------------------------------------------- grupos


async def test_mensagem_em_grupo_e_ignorada(dp, bot, telegram, session):
    await mensagem(dp, bot, '/gasto 45 debito "mercado"', chat=GRUPO)
    await mensagem(dp, bot, "/geral", chat=GRUPO)
    assert telegram.chamadas == []
    assert await despesas(session) == []


async def test_clique_em_grupo_e_ignorado(dp, bot, telegram, repo, session):
    despesa = await _criar_despesa(repo)
    await clique(dp, bot, f"novacat:{despesa.id}:Estudos", usuario=INTRUSO, chat=GRUPO)
    assert telegram.chamadas == []
    await session.refresh(despesa)
    assert despesa.categoria == "Comida"


# ---------------------------------------------------------------- IDOR na correção


async def test_outro_usuario_nao_altera_categoria(dp, bot, telegram, repo, session):
    despesa = await _criar_despesa(repo)
    await clique(dp, bot, f"novacat:{despesa.id}:Estudos", usuario=INTRUSO)
    await session.refresh(despesa)
    assert despesa.categoria == "Comida"
    assert telegram.alertas() == ["❌ Gasto não encontrado."]


async def test_outro_usuario_nao_abre_correcao(dp, bot, telegram, repo):
    despesa = await _criar_despesa(repo)
    await clique(dp, bot, f"corrigir:{despesa.id}", usuario=INTRUSO)
    assert telegram.alertas() == ["❌ Gasto não encontrado."]


async def test_dono_altera_categoria(dp, bot, repo, session):
    despesa = await _criar_despesa(repo)
    await clique(dp, bot, f"novacat:{despesa.id}:Estudos")
    await session.refresh(despesa)
    assert despesa.categoria == "Estudos"


# ---------------------------------------------------------------- limites de tamanho


async def test_mensagem_longa_e_recusada(dp, bot, telegram, session):
    await mensagem(dp, bot, "45 pix " + "a" * MAX_TEXTO)
    assert "longa demais" in telegram.textos()[-1]
    assert await despesas(session) == []


async def test_descricao_longa_no_fluxo_guiado(dp, bot, telegram, session):
    await mensagem(dp, bot, "/gasto 45 pix")
    await mensagem(dp, bot, "palavra " * 20)  # ~160 caracteres: cabe no texto, não na descrição
    assert "poucas palavras" in telegram.textos()[-1]
    await mensagem(dp, bot, "mercado")
    [despesa] = await despesas(session)
    assert despesa.descricao == "Mercado"


async def test_estado_da_conversa_termina_limpo(dp, bot, session):
    from bot.models import FsmEstado

    await mensagem(dp, bot, "Gastei 20 no cinema")
    assert await session.scalar(select(func.count()).select_from(FsmEstado)) == 1
    await mensagem(dp, bot, "credito")
    assert await session.scalar(select(func.count()).select_from(FsmEstado)) == 0


# ---------------------------------------------------------------- vários gastos


async def test_dois_gastos_completos_numa_mensagem(dp, bot, telegram, session):
    await mensagem(
        dp,
        bot,
        "Gastei 119 reais no mercado ontem, no débito e R$20 na padaria hoje, usando o voucher",
    )
    primeiro, segundo = await despesas(session)
    assert (primeiro.valor, primeiro.forma_pagamento, primeiro.categoria) == (
        Decimal("119.00"),
        "Débito",
        "Comida",
    )
    assert (segundo.valor, segundo.forma_pagamento, segundo.descricao) == (
        Decimal("20.00"),
        "Voucher",
        "Padaria",
    )
    assert primeiro.data < segundo.data  # ontem / hoje
    confirmacoes = [t for t in telegram.textos() if "registrado" in t]
    assert len(confirmacoes) == 2
    assert "Gasto 1 de 2" in confirmacoes[0] and "Gasto 2 de 2" in confirmacoes[1]


async def test_segundo_gasto_incompleto_pergunta_so_por_ele(dp, bot, telegram, session):
    await mensagem(dp, bot, "45 pix mercado e 20 padaria, 10 dinheiro feira")
    # 1º salvo; o 2º não tem forma de pagamento (há formas conflitantes, sem herança)
    assert len(await despesas(session)) == 1
    assert "Gasto 2 de 3" in telegram.textos()[-1]
    assert "Como você pagou" in telegram.textos()[-1]

    await clique(dp, bot, "forma:Voucher")
    salvos = await despesas(session)
    assert [(d.descricao, d.forma_pagamento) for d in salvos] == [
        ("Mercado", "Pix"),
        ("Padaria", "Voucher"),
        ("Feira", "Dinheiro"),
    ]


async def test_cancelar_descarta_a_fila(dp, bot, telegram, session):
    await mensagem(dp, bot, "45 mercado, 20 padaria e 10 feira")  # nenhum tem forma
    await mensagem(dp, bot, "/cancelar")
    assert telegram.textos()[-1] == "🚫 3 registros cancelados."
    assert await despesas(session) == []


async def test_gastos_demais_numa_mensagem(dp, bot, telegram, session):
    await mensagem(dp, bot, ", ".join(f"{v} pix mercado" for v in range(1, 8)))
    assert "até 5 gastos" in telegram.textos()[-1]
    assert await despesas(session) == []


# ---------------------------------------------------------------- dashboard


async def test_dashboard_envia_botao_do_mini_app(dp, bot, telegram, monkeypatch):
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "bot.vercel.app")
    await mensagem(dp, bot, "/dashboard")
    teclado = telegram.chamadas[-1].reply_markup
    botao = teclado.inline_keyboard[0][0]
    assert botao.web_app.url == "https://bot.vercel.app/api/dashboard"


async def test_dashboard_sem_url_configurada(dp, bot, telegram, monkeypatch):
    monkeypatch.delenv("VERCEL_PROJECT_PRODUCTION_URL", raising=False)
    await mensagem(dp, bot, "/dashboard")
    assert "não está configurado" in telegram.textos()[-1]
