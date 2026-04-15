from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    """One row per /api/analyze call. This is the audit trail, not application config --
    swapping SQLite for PostgreSQL means changing DATABASE_URL, not this schema.
    """

    __tablename__ = "analysis_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    feedback: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(20))

    sentiment: Mapped[str] = mapped_column(String(20))
    urgency: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)

    latency_ms: Mapped[float] = mapped_column(Float)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
