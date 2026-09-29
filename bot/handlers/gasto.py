from datetime import date
from decimal import Decimal
from html import escape

import structlog
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.keyboards import (
    CategoriaCB,
    CorrigirCB,
    FormaCB,
    NovaCategoriaCB,
    teclado_categorias,
    teclado_corrigir,
    teclado_formas,
    teclado_nova_categoria,
)
from bot.relogio import hoje
from bot.repositories.despesa_repository import DespesaRepository
from bot.services import parser_service
from bot.services.categorizacao_service import CATEGORIAS, categorizar
from bot.services.formatador_service import (
    alerta,
    erro,
    formatar_brl,
    formatar_confirmacao,
)
from bot.services.parser_service import DespesaParcial
from bot.services.texto import normalizar
from bot.states.registro_gasto import RegistroGasto

router = Router(name="gasto")
log = structlog.get_logger()

DICA_USO = (
    'Para registrar um gasto, use <code>/gasto 45 debito "mercado"</code> '
    "ou escreva algo como <i>Gastei 45 reais no mercado com débito</i>.\n"
    "Dá para registrar vários de uma vez: <i>45 no mercado no pix e 20 na padaria</i>.\n"
    "Veja todos os comandos em /ajuda."
)


# ---------------------------------------------------------------- fluxo principal


def _erro_gastos_demais() -> str:
    return erro(
        f"Registre até {parser_service.MAX_GASTOS} gastos por mensagem. "
        "Divida em mais de uma mensagem."
    )


def _serializar(parcial: DespesaParcial) -> dict[str, str | None]:
    """Gasto parcial no formato guardado no FSM (JSON: valor em str, data ISO)."""
    return {
        "valor": str(parcial.valor) if parcial.valor is not None else None,
        "forma": parcial.forma_pagamento,
        "data": parcial.data.isoformat() if parcial.data is not None else None,
        "descricao": parcial.descricao,
    }


async def _iniciar(
    message: Message, state: FSMContext, session: AsyncSession, parciais: list[DespesaParcial]
) -> None:
    """Começa o registro de um ou mais gastos: o primeiro é o atual, os demais vão
    para a `fila` e são processados em ordem conforme cada um é salvo."""
    # Sem texto, valor ou descrição no log: são dados financeiros do usuário
    faltando = [
        [c for c in ("valor", "forma_pagamento", "data", "descricao") if getattr(p, c) is None]
        for p in parciais
    ]
    log.debug("gasto_parseado", gastos=len(parciais), campos_faltando=faltando)
    primeiro, *resto = [_serializar(p) for p in parciais]
    await state.set_data({**primeiro, "fila": resto, "indice": 1, "total": len(parciais)})
    await _avancar(message, state, session, message.from_user.id)


def _prefixo(dados: dict) -> str:
    """Prefixo "Gasto 2 de 3 · " quando a mensagem tinha vários gastos."""
    total = dados.get("total", 1)
    return f"<b>Gasto {dados.get('indice', 1)} de {total}</b> · " if total > 1 else ""


async def _avancar(
    message: Message, state: FSMContext, session: AsyncSession, user_id: int
) -> None:
    """Pergunta o primeiro campo que faltar; com tudo preenchido, categoriza e salva.

    `user_id` vem sempre de `from_user` (quem enviou a mensagem ou clicou no botão).
    Em callbacks, `message` é a mensagem *do bot*, então não serve para identificar o dono.
    """
    dados = await state.get_data()

    if not dados.get("valor"):
        await state.set_state(RegistroGasto.aguardando_valor)
        await message.answer(
            _prefixo(dados) + "💰 Qual foi o valor do gasto? (ex: <code>45,90</code>)"
        )
        return
    if not dados.get("data"):
        await state.set_state(RegistroGasto.aguardando_data)
        await message.answer(
            _prefixo(dados)
            + alerta(
                "Não entendi a data. Quando foi o gasto? (ex: <code>hoje</code>, "
                "<code>ontem</code>, <code>05/09</code>)"
            )
        )
        return
    if not dados.get("forma"):
        await state.set_state(RegistroGasto.aguardando_forma)
        await message.answer(
            _prefixo(dados) + f"💳 Como você pagou os {formatar_brl(Decimal(dados['valor']))}?",
            reply_markup=teclado_formas(),
        )
        return
    if not dados.get("descricao"):
        await state.set_state(RegistroGasto.aguardando_descricao)
        await message.answer(
            _prefixo(dados)
            + f"📝 Com o que foi o gasto de {formatar_brl(Decimal(dados['valor']))}? "
            "(ex: <i>mercado</i>, <i>cinema</i>)"
        )
        return

    categoria = dados.get("categoria") or categorizar(dados["descricao"])
    if categoria is None:
        await state.set_state(RegistroGasto.aguardando_categoria)
        await message.answer(
            _prefixo(dados)
            + f"🏷️ Em qual categoria se encaixa <b>{escape(dados['descricao'])}</b>?",
            reply_markup=teclado_categorias(),
        )
        return

    despesa = await DespesaRepository(session).criar(
        user_id=user_id,
        valor=Decimal(dados["valor"]),
        forma_pagamento=dados["forma"],
        data=date.fromisoformat(dados["data"]),
        descricao=dados["descricao"],
        categoria=categoria,
    )
    log.info("despesa_registrada", despesa_id=despesa.id, user_id=despesa.user_id)
    total, indice = dados.get("total", 1), dados.get("indice", 1)
    titulo = f"✅ Gasto {indice} de {total} registrado!" if total > 1 else "✅ Gasto registrado!"
    await message.answer(
        formatar_confirmacao(despesa, titulo=titulo), reply_markup=teclado_corrigir(despesa.id)
    )

    fila = dados.get("fila") or []
    if not fila:
        await state.clear()
        return
    proximo, *resto = fila
    await state.set_data({**proximo, "fila": resto, "indice": indice + 1, "total": total})
    await _avancar(message, state, session, user_id)


# ---------------------------------------------------------------- entradas


@router.message(F.text.len() > parser_service.MAX_TEXTO)
async def texto_longo_demais(message: Message) -> None:
    await message.answer(
        erro(f"Mensagem longa demais (máximo de {parser_service.MAX_TEXTO} caracteres).")
    )


@router.message(Command("cancelar"))
async def cancelar(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("ℹ️ Não há nenhum registro em andamento.")
        return
    pendentes = 1 + len((await state.get_data()).get("fila") or [])
    await state.clear()
    if pendentes > 1:
        await message.answer(f"🚫 {pendentes} registros cancelados.")
    else:
        await message.answer("🚫 Registro cancelado.")


@router.message(Command("gasto"))
async def cmd_gasto(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    parciais = parser_service.parse_varios(command.args or "", hoje(settings.timezone))
    if len(parciais) > parser_service.MAX_GASTOS:
        await message.answer(_erro_gastos_demais())
        return
    await _iniciar(message, state, session, parciais)


@router.message(RegistroGasto.aguardando_valor, F.text, ~F.text.startswith("/"))
async def receber_valor(message: Message, state: FSMContext, session: AsyncSession) -> None:
    valor = parser_service.parse_valor(message.text)
    if valor is None:
        await message.answer(erro("Valor inválido. Envie só o número, ex: <code>45,90</code>"))
        return
    await state.update_data(valor=str(valor))
    await _avancar(message, state, session, message.from_user.id)


@router.message(RegistroGasto.aguardando_data, F.text, ~F.text.startswith("/"))
async def receber_data(
    message: Message, state: FSMContext, session: AsyncSession, settings: Settings
) -> None:
    data = parser_service.parse_data(message.text, hoje(settings.timezone))
    if data is None:
        await message.answer(
            erro("Data inválida. Use <code>hoje</code>, <code>ontem</code> ou <code>dd/mm</code>.")
        )
        return
    # `data` é também o nome do parâmetro posicional de update_data
    await state.update_data({"data": data.isoformat()})
    await _avancar(message, state, session, message.from_user.id)


@router.message(RegistroGasto.aguardando_forma, F.text, ~F.text.startswith("/"))
async def receber_forma_texto(message: Message, state: FSMContext, session: AsyncSession) -> None:
    forma = parser_service.parse_forma_pagamento(message.text)
    if forma is None:
        await message.answer(
            erro("Forma de pagamento não reconhecida. Escolha uma opção:"),
            reply_markup=teclado_formas(),
        )
        return
    await state.update_data(forma=forma)
    await _avancar(message, state, session, message.from_user.id)


@router.callback_query(RegistroGasto.aguardando_forma, FormaCB.filter())
async def receber_forma_botao(
    callback: CallbackQuery, callback_data: FormaCB, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(forma=callback_data.forma)
    await callback.answer()
    await callback.message.edit_text(f"💳 Pagamento: <b>{callback_data.forma}</b>")
    await _avancar(callback.message, state, session, callback.from_user.id)


@router.message(RegistroGasto.aguardando_descricao, F.text, ~F.text.startswith("/"))
async def receber_descricao(message: Message, state: FSMContext, session: AsyncSession) -> None:
    descricao = parser_service.limpar_descricao(message.text)
    if descricao is None:
        await message.answer(
            erro(
                "Descreva o gasto em poucas palavras (até "
                f"{parser_service.MAX_DESCRICAO} caracteres), ex: <i>mercado</i>."
            )
        )
        return
    await state.update_data(descricao=descricao)
    await _avancar(message, state, session, message.from_user.id)


@router.message(RegistroGasto.aguardando_categoria, F.text, ~F.text.startswith("/"))
async def receber_categoria_texto(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    escolhida = next((c for c in CATEGORIAS if normalizar(c) == normalizar(message.text)), None)
    if escolhida is None:
        await message.answer(
            alerta("Escolha uma das categorias abaixo:"), reply_markup=teclado_categorias()
        )
        return
    await state.update_data(categoria=escolhida)
    await _avancar(message, state, session, message.from_user.id)


@router.callback_query(RegistroGasto.aguardando_categoria, CategoriaCB.filter())
async def receber_categoria_botao(
    callback: CallbackQuery, callback_data: CategoriaCB, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(categoria=callback_data.categoria)
    await callback.answer()
    await callback.message.delete()
    await _avancar(callback.message, state, session, callback.from_user.id)


# ---------------------------------------------------------------- correção de categoria


@router.callback_query(CorrigirCB.filter())
async def corrigir_categoria(
    callback: CallbackQuery, callback_data: CorrigirCB, session: AsyncSession
) -> None:
    despesa = await DespesaRepository(session).obter(
        callback_data.despesa_id, callback.from_user.id
    )
    if despesa is None:
        await callback.answer("❌ Gasto não encontrado.", show_alert=True)
        return
    await callback.answer("Escolha a nova categoria")
    await callback.message.edit_reply_markup(
        reply_markup=teclado_nova_categoria(callback_data.despesa_id)
    )


@router.callback_query(NovaCategoriaCB.filter())
async def salvar_nova_categoria(
    callback: CallbackQuery, callback_data: NovaCategoriaCB, session: AsyncSession
) -> None:
    despesa = await DespesaRepository(session).atualizar_categoria(
        callback_data.despesa_id, callback.from_user.id, callback_data.categoria
    )
    if despesa is None:
        await callback.answer("❌ Gasto não encontrado.", show_alert=True)
        return
    await callback.answer("✅ Categoria atualizada")
    await callback.message.edit_text(
        formatar_confirmacao(despesa, titulo="✏️ Categoria atualizada!"),
        reply_markup=teclado_corrigir(despesa.id),
    )


# ---------------------------------------------------------------- fallbacks


@router.callback_query(FormaCB.filter())
@router.callback_query(CategoriaCB.filter())
async def botao_expirado(callback: CallbackQuery) -> None:
    await callback.answer("⚠️ Esse registro expirou. Comece de novo com /gasto.", show_alert=True)


@router.message(StateFilter(None), F.text.startswith("/"))
async def comando_desconhecido(message: Message) -> None:
    await message.answer(erro("Comando não reconhecido.") + "\n" + DICA_USO)


@router.message(StateFilter(None), F.text)
async def texto_livre(
    message: Message, state: FSMContext, session: AsyncSession, settings: Settings
) -> None:
    parciais = parser_service.parse_varios(message.text, hoje(settings.timezone))
    if all(p.valor is None for p in parciais):
        await message.answer(alerta("Não encontrei um valor na sua mensagem.") + "\n" + DICA_USO)
        return
    if len(parciais) > parser_service.MAX_GASTOS:
        await message.answer(_erro_gastos_demais())
        return
    await _iniciar(message, state, session, parciais)


@router.message(F.text.startswith("/"))
async def comando_durante_registro(message: Message) -> None:
    await message.answer(
        alerta("Há um registro em andamento. Responda a pergunta acima ou use /cancelar.")
    )
