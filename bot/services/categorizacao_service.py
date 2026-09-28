import re

from bot.services.texto import normalizar

CATEGORIAS: dict[str, str] = {
    "Lazer": "🎮",
    "Estudos": "📚",
    "Comida": "🍔",
    "Investimentos": "📈",
    "Outros": "📦",
}

# Palavra-chave (sem acento, minúscula) → categoria. Expanda conforme o uso.
PALAVRAS_CHAVE: dict[str, str] = {
    # Comida
    "mercado": "Comida", "supermercado": "Comida", "restaurante": "Comida",
    "ifood": "Comida", "delivery": "Comida", "lanche": "Comida", "padaria": "Comida",
    "almoco": "Comida", "jantar": "Comida", "cafe": "Comida", "pizza": "Comida",
    "hamburguer": "Comida", "acougue": "Comida", "feira": "Comida", "hortifruti": "Comida",
    "comida": "Comida", "sorvete": "Comida", "rappi": "Comida",
    # Estudos
    "curso": "Estudos", "livro": "Estudos", "faculdade": "Estudos", "apostila": "Estudos",
    "escola": "Estudos", "mensalidade": "Estudos", "udemy": "Estudos", "alura": "Estudos",
    "caderno": "Estudos", "material escolar": "Estudos", "ingles": "Estudos",
    # Lazer
    "cinema": "Lazer", "jogo": "Lazer", "game": "Lazer", "videogame": "Lazer",
    "steam": "Lazer", "playstation": "Lazer", "xbox": "Lazer", "nintendo": "Lazer",
    "show": "Lazer", "shopping": "Lazer", "bar": "Lazer", "cerveja": "Lazer",
    "netflix": "Lazer", "spotify": "Lazer", "viagem": "Lazer", "teatro": "Lazer",
    "festa": "Lazer", "balada": "Lazer",
    # Investimentos
    "aporte": "Investimentos", "tesouro": "Investimentos", "cdb": "Investimentos",
    "acao": "Investimentos", "acoes": "Investimentos", "investimento": "Investimentos",
    "fii": "Investimentos", "poupanca": "Investimentos", "cripto": "Investimentos",
    "bitcoin": "Investimentos", "lci": "Investimentos", "lca": "Investimentos",
}  # fmt: skip

# Palavras-chave compostas primeiro
_PADROES = [
    (re.compile(rf"\b{re.escape(chave)}s?\b"), categoria)
    for chave, categoria in sorted(PALAVRAS_CHAVE.items(), key=lambda kv: -len(kv[0]))
]


def categorizar(descricao: str) -> str | None:
    """Retorna a categoria pela primeira palavra-chave encontrada, ou None."""
    texto = normalizar(descricao)
    for padrao, categoria in _PADROES:
        if padrao.search(texto):
            return categoria
    return None


def icone(categoria: str) -> str:
    return CATEGORIAS.get(categoria, "📦")
