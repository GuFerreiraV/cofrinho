"""Dashboard (Mini App do Telegram), função serverless da Vercel.

GET  /api/dashboard   página (HTML estático)
POST /api/dashboard   dados: {initData, periodo, categoria} → JSON
"""

import sys
from pathlib import Path

# Garante que o pacote `bot` (na raiz do projeto) seja importável na Vercel
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import structlog  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from bot.app import configurar_logging  # noqa: E402
from bot.config import get_settings  # noqa: E402
from bot.db import criar_engine, criar_sessionmaker  # noqa: E402
from bot.relogio import hoje  # noqa: E402
from bot.repositories.despesa_repository import DespesaRepository  # noqa: E402
from bot.services.dashboard_service import DashboardService, Periodo  # noqa: E402
from bot.web.auth import usuario_do_dashboard  # noqa: E402

settings = get_settings()
configurar_logging(settings.log_level)
log = structlog.get_logger()

engine = criar_engine(settings.database_url.get_secret_value())
sessionmaker = criar_sessionmaker(engine)
PAGINA = (RAIZ / "bot" / "web" / "dashboard.html").read_text(encoding="utf-8")
SEM_CACHE = {"Cache-Control": "no-store"}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class Filtros(BaseModel):
    init_data: str = Field(default="", alias="initData", max_length=4096)
    periodo: Periodo = "mes"
    categoria: str | None = Field(default=None, max_length=50)


@app.get("/api/dashboard")
async def pagina() -> HTMLResponse:
    return HTMLResponse(PAGINA, headers={"Cache-Control": "no-cache"})


@app.post("/api/dashboard")
async def dados(filtros: Filtros) -> JSONResponse:
    user_id = usuario_do_dashboard(filtros.init_data, settings)
    if user_id is None:
        return JSONResponse({"erro": "não autorizado"}, status_code=401, headers=SEM_CACHE)
    async with sessionmaker() as session:
        servico = DashboardService(DespesaRepository(session), hoje(settings.timezone))
        try:
            resumo = await servico.resumo(user_id, filtros.periodo, filtros.categoria)
        except ValueError:
            return JSONResponse({"erro": "filtro inválido"}, status_code=422, headers=SEM_CACHE)
    return JSONResponse(resumo, headers=SEM_CACHE)
