from bot.services.categorizacao_service import categorizar


def test_palavras_chave():
    assert categorizar("Mercado") == "Comida"
    assert categorizar("curso de inglês") == "Estudos"
    assert categorizar("Cinema com amigos") == "Lazer"
    assert categorizar("aporte no tesouro") == "Investimentos"


def test_ignora_acento_e_maiusculas():
    assert categorizar("ALMOÇO") == "Comida"
    assert categorizar("Ações da Petrobras") == "Investimentos"


def test_plural():
    assert categorizar("livros") == "Estudos"


def test_palavra_parcial_nao_casa():
    assert categorizar("barbearia") is None


def test_sem_palavra_chave_retorna_none():
    assert categorizar("xpto") is None
