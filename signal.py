from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.database import Base

if TYPE_CHECKING:
    from api.models.session import SessionTrade


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset: Mapped[str] = mapped_column(String(20), index=True)
    asset_category: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[str] = mapped_column(String(4))
    timeframe: Mapped[str] = mapped_column(String(5), index=True)
    duration_sec: Mapped[int] = mapped_column(Integer)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    confidence: Mapped[float]
    indicator_score: Mapped[float]
    ml_confidence: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    result: Mapped[str] = mapped_column(String(10), default="PENDING")
    agent_id: Mapped[str] = mapped_column(String(20))

    trades: Mapped[list["SessionTrade"]] = relationship(back_populates="signal")

