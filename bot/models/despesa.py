from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Despesa(Base):
    __tablename__ = "despesas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)  # chat_id do Telegram
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    forma_pagamento: Mapped[str] = mapped_column(index=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    descricao: Mapped[str]
    categoria: Mapped[str] = mapped_column(index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
