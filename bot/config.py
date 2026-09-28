from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    database_url: str = "sqlite+aiosqlite:///./data/financeiro.db"
    timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"
    # Produção (Vercel): URL pública do endpoint e segredo enviado pelo Telegram em cada update
    webhook_url: str | None = None
    webhook_secret: SecretStr | None = None


def get_settings() -> Settings:
    return Settings()
