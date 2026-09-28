from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.despesa import Base


class FsmEstado(Base):
    """Estado da conversa (FSM do aiogram), persistido entre invocações serverless."""

    __tablename__ = "fsm_estados"

    chave: Mapped[str] = mapped_column(String(255), primary_key=True)
    estado: Mapped[str | None] = mapped_column(String(255))
    dados: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
