import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparações tolerantes."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()
