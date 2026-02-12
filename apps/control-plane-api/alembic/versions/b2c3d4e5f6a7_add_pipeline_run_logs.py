"""add pipeline_run_logs table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-11

Stores log entries per pipeline run for MVP run monitoring.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("level", sa.Text(), nullable=False, server_default="INFO"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_run_logs_run_id_ts", "pipeline_run_logs", ["run_id", "ts"])
    op.create_index("ix_pipeline_run_logs_tenant_id_ts", "pipeline_run_logs", ["tenant_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_logs_tenant_id_ts", table_name="pipeline_run_logs")
    op.drop_index("ix_pipeline_run_logs_run_id_ts", table_name="pipeline_run_logs")
    op.drop_table("pipeline_run_logs")
