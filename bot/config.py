from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    # SecretStr: a URL do Neon contém a senha do banco e não pode aparecer em logs/repr
    database_url: SecretStr = SecretStr("sqlite+aiosqlite:///./data/financeiro.db")
    timezone: str = "America/Sao_Paulo"
    log_level: str = "INFO"
    # Produção (Vercel): URL pública do endpoint e segredo enviado pelo Telegram em cada update
    webhook_url: str | None = None
    webhook_secret: SecretStr | None = None
    # Dashboard (Mini App). Sem DASHBOARD_URL, usa o domínio de produção da Vercel
    dashboard_url: str | None = None
    # Só desenvolvimento local: abre o dashboard no navegador como este usuário,
    # sem initData do Telegram. Ignorado quando roda na Vercel.
    dashboard_dev_user_id: int | None = None


def get_settings() -> Settings:
    return Settings()
