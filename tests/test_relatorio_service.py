from datetime import date
from decimal import Decimal

from bot.services.relatorio_service import RelatorioService

HOJE = date(2026, 9, 26)  # sábado; semana começa em 21/09 (segunda)
USER = 1
OUTRO_USER = 2


async def _gasto(repo, valor, data, categoria="Comida", user_id=USER):
    await repo.criar(
        user_id=user_id,
        valor=Decimal(valor),
        forma_pagamento="Pix",
        data=data,
        descricao="teste",
        categoria=categoria,
    )


async def _popular(repo):
    await _gasto(repo, "10.00", HOJE)
    await _gasto(repo, "5.50", HOJE, "Lazer")
    await _gasto(repo, "20.00", date(2026, 9, 21))  # segunda desta semana
    await _gasto(repo, "30.00", date(2026, 9, 20))  # domingo da semana passada
    await _gasto(repo, "40.00", date(2026, 9, 1))
    await _gasto(repo, "50.00", date(2026, 8, 31))
    await _gasto(repo, "999.00", HOJE, user_id=OUTRO_USER)


async def test_diario(repo):
    await _popular(repo)
    titulo, totais = await RelatorioService(repo, HOJE).diario(USER)
    assert "26/09/2026" in titulo
    assert totais == {"Comida": Decimal("10.00"), "Lazer": Decimal("5.50")}


async def test_semanal_comeca_na_segunda(repo):
    await _popular(repo)
    titulo, totais = await RelatorioService(repo, HOJE).semanal(USER)
    assert "21/09" in titulo
    assert totais == {"Comida": Decimal("30.00"), "Lazer": Decimal("5.50")}


async def test_mensal(repo):
    await _popular(repo)
    titulo, totais = await RelatorioService(repo, HOJE).mensal(USER)
    assert titulo == "📊 Resumo de Setembro/2026"
    assert totais == {"Comida": Decimal("100.00"), "Lazer": Decimal("5.50")}


async def test_geral_isola_usuarios(repo):
    await _popular(repo)
    _, totais = await RelatorioService(repo, HOJE).geral(USER)
    assert totais == {"Comida": Decimal("150.00"), "Lazer": Decimal("5.50")}
    _, outro = await RelatorioService(repo, HOJE).geral(OUTRO_USER)
    assert outro == {"Comida": Decimal("999.00")}


async def test_sem_gastos(repo):
    _, totais = await RelatorioService(repo, HOJE).geral(USER)
    assert totais == {}
