from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.categorizacao_service import CATEGORIAS
from bot.services.formatador_service import ICONES_PAGAMENTO
from bot.services.parser_service import FORMAS_PAGAMENTO


class FormaCB(CallbackData, prefix="forma"):
    forma: str


class CategoriaCB(CallbackData, prefix="cat"):
    categoria: str


class CorrigirCB(CallbackData, prefix="corrigir"):
    despesa_id: int


class NovaCategoriaCB(CallbackData, prefix="novacat"):
    despesa_id: int
    categoria: str


def teclado_formas() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for forma in FORMAS_PAGAMENTO:
        kb.button(text=f"{ICONES_PAGAMENTO[forma]} {forma}", callback_data=FormaCB(forma=forma))
    kb.adjust(2)
    return kb.as_markup()


def teclado_categorias() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for categoria, icone in CATEGORIAS.items():
        kb.button(text=f"{icone} {categoria}", callback_data=CategoriaCB(categoria=categoria))
    kb.adjust(2)
    return kb.as_markup()


def teclado_nova_categoria(despesa_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for categoria, icone in CATEGORIAS.items():
        kb.button(
            text=f"{icone} {categoria}",
            callback_data=NovaCategoriaCB(despesa_id=despesa_id, categoria=categoria),
        )
    kb.adjust(2)
    return kb.as_markup()


def teclado_corrigir(despesa_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Corrigir categoria", callback_data=CorrigirCB(despesa_id=despesa_id))
    return kb.as_markup()
