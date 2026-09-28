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
    "Veja todos os comandos em /ajuda."
)


# ---------------------------------------------------------------- fluxo principal


async def _iniciar(
    message: Message, state: FSMContext, session: AsyncSession, parcial: DespesaParcial
) -> None:
    log.debug("gasto_parseado", texto=message.text, parcial=parcial)
    await state.set_data(
        {
            "valor": str(parcial.valor) if parcial.valor is not None else None,
            "forma": parcial.forma_pagamento,
            "data": parcial.data.isoformat() if parcial.data is not None else None,
            "descricao": parcial.descricao,
        }
    )
    await _avancar(message, state, session)


async def _avancar(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Pergunta o primeiro campo que faltar; com tudo preenchido, categoriza e salva."""
    dados = await state.get_data()

    if not dados.get("valor"):
        await state.set_state(RegistroGasto.aguardando_valor)
        await message.answer("💰 Qual foi o valor do gasto? (ex: <code>45,90</code>)")
        return
    if not dados.get("data"):
        await state.set_state(RegistroGasto.aguardando_data)
        await message.answer(
            alerta(
                "Não entendi a data. Quando foi o gasto? (ex: <code>hoje</code>, "
                "<code>ontem</code>, <code>05/09</code>)"
            )
        )
        return
    if not dados.get("forma"):
        await state.set_state(RegistroGasto.aguardando_forma)
        await message.answer(
            f"💳 Como você pagou os {formatar_brl(Decimal(dados['valor']))}?",
            reply_markup=teclado_formas(),
        )
        return
    if not dados.get("descricao"):
        await state.set_state(RegistroGasto.aguardando_descricao)
        await message.answer("📝 Com o que foi o gasto? (ex: <i>mercado</i>, <i>cinema</i>)")
        return

    categoria = dados.get("categoria") or categorizar(dados["descricao"])
    if categoria is None:
        await state.set_state(RegistroGasto.aguardando_categoria)
        await message.answer(
            f"🏷️ Em qual categoria se encaixa <b>{escape(dados['descricao'])}</b>?",
            reply_markup=teclado_categorias(),
        )
        return

    despesa = await DespesaRepository(session).criar(
        user_id=message.chat.id,
        valor=Decimal(dados["valor"]),
        forma_pagamento=dados["forma"],
        data=date.fromisoformat(dados["data"]),
        descricao=dados["descricao"],
        categoria=categoria,
    )
    await state.clear()
    log.info("despesa_registrada", despesa_id=despesa.id, user_id=despesa.user_id)
    await message.answer(formatar_confirmacao(despesa), reply_markup=teclado_corrigir(despesa.id))


# ---------------------------------------------------------------- entradas


@router.message(Command("cancelar"))
async def cancelar(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("ℹ️ Não há nenhum registro em andamento.")
        return
    await state.clear()
    await message.answer("🚫 Registro cancelado.")


@router.message(Command("gasto"))
async def cmd_gasto(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    parcial = parser_service.parse(command.args or "", hoje(settings.timezone))
    await _iniciar(message, state, session, parcial)


@router.message(RegistroGasto.aguardando_valor, F.text, ~F.text.startswith("/"))
async def receber_valor(message: Message, state: FSMContext, session: AsyncSession) -> None:
    valor = parser_service.parse_valor(message.text)
    if valor is None:
        await message.answer(erro("Valor inválido. Envie só o número, ex: <code>45,90</code>"))
        return
    await state.update_data(valor=str(valor))
    await _avancar(message, state, session)


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
    await _avancar(message, state, session)


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
    await _avancar(message, state, session)


@router.callback_query(RegistroGasto.aguardando_forma, FormaCB.filter())
async def receber_forma_botao(
    callback: CallbackQuery, callback_data: FormaCB, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(forma=callback_data.forma)
    await callback.answer()
    await callback.message.edit_text(f"💳 Pagamento: <b>{callback_data.forma}</b>")
    await _avancar(callback.message, state, session)


@router.message(RegistroGasto.aguardando_descricao, F.text, ~F.text.startswith("/"))
async def receber_descricao(message: Message, state: FSMContext, session: AsyncSession) -> None:
    descricao = parser_service.limpar_descricao(message.text)
    if descricao is None:
        await message.answer(erro("Descreva o gasto em poucas palavras, ex: <i>mercado</i>."))
        return
    await state.update_data(descricao=descricao)
    await _avancar(message, state, session)


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
    await _avancar(message, state, session)


@router.callback_query(RegistroGasto.aguardando_categoria, CategoriaCB.filter())
async def receber_categoria_botao(
    callback: CallbackQuery, callback_data: CategoriaCB, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(categoria=callback_data.categoria)
    await callback.answer()
    await callback.message.delete()
    await _avancar(callback.message, state, session)


# ---------------------------------------------------------------- correção de categoria


@router.callback_query(CorrigirCB.filter())
async def corrigir_categoria(callback: CallbackQuery, callback_data: CorrigirCB) -> None:
    await callback.answer("Escolha a nova categoria")
    await callback.message.edit_reply_markup(
        reply_markup=teclado_nova_categoria(callback_data.despesa_id)
    )


@router.callback_query(NovaCategoriaCB.filter())
async def salvar_nova_categoria(
    callback: CallbackQuery, callback_data: NovaCategoriaCB, session: AsyncSession
) -> None:
    despesa = await DespesaRepository(session).atualizar_categoria(
        callback_data.despesa_id, callback.message.chat.id, callback_data.categoria
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
    parcial = parser_service.parse(message.text, hoje(settings.timezone))
    if parcial.valor is None:
        await message.answer(alerta("Não encontrei um valor na sua mensagem.") + "\n" + DICA_USO)
        return
    await _iniciar(message, state, session, parcial)


@router.message(F.text.startswith("/"))
async def comando_durante_registro(message: Message) -> None:
    await message.answer(
        alerta("Há um registro em andamento. Responda a pergunta acima ou use /cancelar.")
    )
