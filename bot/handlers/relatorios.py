from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.relogio import hoje
from bot.repositories.despesa_repository import DespesaRepository
from bot.services.formatador_service import formatar_relatorio
from bot.services.relatorio_service import RelatorioService

router = Router(name="relatorios")


def _servico(session: AsyncSession, settings: Settings) -> RelatorioService:
    return RelatorioService(DespesaRepository(session), hoje(settings.timezone))


@router.message(Command("diario"))
async def diario(message: Message, session: AsyncSession, settings: Settings) -> None:
    titulo, totais = await _servico(session, settings).diario(message.from_user.id)
    await message.answer(formatar_relatorio(titulo, totais))


@router.message(Command("semanal"))
async def semanal(message: Message, session: AsyncSession, settings: Settings) -> None:
    titulo, totais = await _servico(session, settings).semanal(message.from_user.id)
    await message.answer(formatar_relatorio(titulo, totais))


@router.message(Command("mensal"))
async def mensal(message: Message, session: AsyncSession, settings: Settings) -> None:
    titulo, totais = await _servico(session, settings).mensal(message.from_user.id)
    await message.answer(formatar_relatorio(titulo, totais))


@router.message(Command("geral"))
async def geral(message: Message, session: AsyncSession, settings: Settings) -> None:
    titulo, totais = await _servico(session, settings).geral(message.from_user.id)
    await message.answer(formatar_relatorio(titulo, totais))
