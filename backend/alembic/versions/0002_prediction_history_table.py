"""Prediction history table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

prediction_history_status_enum = postgresql.ENUM(
    "pending",
    "success",
    "partial_success",
    "failed",
    name="prediction_history_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    prediction_history_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "prediction_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "request_id",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            prediction_history_status_enum,
            nullable=False,
        ),
        sa.Column(
            "predicted_class",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "agreement_ratio",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "participating_models",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_prediction_history_request_id",
        "prediction_history",
        ["request_id"],
    )

    op.create_index(
        "ix_prediction_history_user_id",
        "prediction_history",
        ["user_id"],
    )

    op.create_index(
        "ix_prediction_history_status",
        "prediction_history",
        ["status"],
    )

    op.create_index(
        "ix_prediction_history_created_at",
        "prediction_history",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prediction_history_created_at",
        table_name="prediction_history",
    )

    op.drop_index(
        "ix_prediction_history_status",
        table_name="prediction_history",
    )

    op.drop_index(
        "ix_prediction_history_user_id",
        table_name="prediction_history",
    )

    op.drop_index(
        "ix_prediction_history_request_id",
        table_name="prediction_history",
    )

    op.drop_table("prediction_history")

    prediction_history_status_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )