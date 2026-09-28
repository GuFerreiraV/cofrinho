from aiogram.fsm.state import State, StatesGroup


class RegistroGasto(StatesGroup):
    aguardando_valor = State()
    aguardando_forma = State()
    aguardando_descricao = State()
    aguardando_categoria = State()
    aguardando_data = State()  # só quando a data informada é inválida
