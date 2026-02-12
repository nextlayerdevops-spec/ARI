"""add pipeline run lifecycle columns

Revision ID: 3f1739d6108c
Revises: f1e1d445c1d4
Create Date: 2026-02-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f1739d6108c"
down_revision: Union[str, Sequence[str], None] = "f1e1d445c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("claimed_by", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "updated_at")
    op.drop_column("pipeline_runs", "error_message")
    op.drop_column("pipeline_runs", "heartbeat_at")
    op.drop_column("pipeline_runs", "claimed_by")
    op.drop_column("pipeline_runs", "claimed_at")
