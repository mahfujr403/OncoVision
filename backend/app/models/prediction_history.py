"""PredictionHistoryRecord ORM model (Phase 5.2, ADR-033).

`PredictionHistoryRecord` is the SQLAlchemy-mapped persistence shape for
the domain-level `app.history.prediction_history.PredictionHistory`
record introduced in Phase 5.1 (ADR-032). It is intentionally distinct
from that domain model, the same way `app.models.user.User` is distinct
from any service-layer projection: the ORM model owns column types,
indexes, and foreign keys, while `PredictionHistory` stays a framework-
agnostic Pydantic value object the rest of the codebase (mapper, service,
future router) depends on.

Per ADR-032, Prediction History records are append-only -- no column here
is ever updated after insert, and no method on `PredictionHistoryRecord`
mutates a row. Per ADR-033, persistence is entirely owned by
`app.repositories.prediction_history_repository.SQLAlchemyPredictionHistoryRepository`;
nothing else constructs or writes this model.

`history_metadata` and `summary` are stored as JSON columns holding the
verbatim `model_dump()` of `PredictionHistoryMetadata` and
`PredictionHistorySummary` respectively (ADR-032) -- no field inside them
is recalculated or renormalized at the database layer. `predicted_class`,
`confidence`, and `agreement_ratio` are additionally flattened onto their
own columns, copied from `summary`, purely so future retrieval and
filtering phases (5.3/5.4) can query and sort on them without deserializing
the JSON payload; they are not a second source of truth.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base
from app.history.enums import PredictionHistoryStatus


class PredictionHistoryRecord(Base):
    """Persisted row for a single, immutable `PredictionHistory` record."""

    __tablename__ = "prediction_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PredictionHistoryStatus] = mapped_column(
        SAEnum(
            PredictionHistoryStatus,
            name="prediction_history_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        index=True,
    )

    predicted_class: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    agreement_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    participating_models: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    history_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
