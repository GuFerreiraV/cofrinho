from datetime import date
from decimal import Decimal


async def _criar(repo, user_id=1):
    return await repo.criar(
        user_id=user_id,
        valor=Decimal("45.90"),
        forma_pagamento="Débito",
        data=date(2026, 9, 26),
        descricao="Mercado",
        categoria="Comida",
    )


async def test_criar_e_obter(repo):
    despesa = await _criar(repo)
    assert despesa.id is not None
    assert despesa.criado_em is not None
    obtida = await repo.obter(despesa.id, 1)
    assert obtida.valor == Decimal("45.90")


async def test_obter_de_outro_usuario_retorna_none(repo):
    despesa = await _criar(repo, user_id=1)
    assert await repo.obter(despesa.id, 2) is None


async def test_atualizar_categoria(repo):
    despesa = await _criar(repo)
    atualizada = await repo.atualizar_categoria(despesa.id, 1, "Lazer")
    assert atualizada.categoria == "Lazer"


async def test_atualizar_categoria_de_outro_usuario_nao_altera(repo):
    despesa = await _criar(repo, user_id=1)
    assert await repo.atualizar_categoria(despesa.id, 2, "Lazer") is None
    assert (await repo.obter(despesa.id, 1)).categoria == "Comida"
