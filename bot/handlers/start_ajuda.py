from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message

router = Router(name="start_ajuda")

COMANDOS = [
    BotCommand(command="gasto", description="Registrar um gasto"),
    BotCommand(command="diario", description="Gastos de hoje"),
    BotCommand(command="semanal", description="Gastos da semana"),
    BotCommand(command="mensal", description="Gastos do mês"),
    BotCommand(command="geral", description="Gastos de todo o histórico"),
    BotCommand(command="cancelar", description="Cancelar o registro em andamento"),
    BotCommand(command="dashboard", description="Painel web (em breve)"),
    BotCommand(command="ajuda", description="Lista de comandos"),
]

AJUDA = (
    "<b>💸 Controle Financeiro</b>\n\n"
    "<b>Registrar um gasto</b>\n"
    '• <code>/gasto 45 debito "mercado"</code>\n'
    "• Ou só escreva: <i>Gastei 45 reais no mercado com débito hoje</i>\n"
    "• Se faltar algo, eu pergunto 😉\n\n"
    "<b>Relatórios</b>\n"
    "📅 /diario — gastos de hoje\n"
    "🗓️ /semanal — gastos da semana (desde segunda)\n"
    "📊 /mensal — gastos do mês\n"
    "🏦 /geral — todo o histórico\n\n"
    "<b>Outros</b>\n"
    "🚫 /cancelar — cancela um registro em andamento\n"
    "📈 /dashboard — painel web (em breve)\n\n"
    "💳 Formas de pagamento: Pix, Débito, Crédito, Dinheiro\n"
    "📅 Datas: hoje, ontem, anteontem, 05/09, dia 5, 5 de setembro"
)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("👋 Olá! Eu ajudo você a controlar seus gastos.\n\n" + AJUDA)


@router.message(Command("ajuda", "help"))
async def ajuda(message: Message) -> None:
    await message.answer(AJUDA)


@router.message(Command("dashboard"))
async def dashboard(message: Message) -> None:
    await message.answer("🚧 O dashboard web está em construção. Em breve!")
