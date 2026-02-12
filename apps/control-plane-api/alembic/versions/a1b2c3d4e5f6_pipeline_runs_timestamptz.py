"""pipeline_runs created_at started_at finished_at to timestamptz

Revision ID: a1b2c3d4e5f6
Revises: 3f1739d6108c
Create Date: 2026-02-12

Converts timestamp without time zone to timestamptz so API returns
timezone-aware values (with offset). Existing values interpreted as UTC.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3f1739d6108c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pipeline_runs
          ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
          ALTER COLUMN started_at TYPE timestamptz USING started_at AT TIME ZONE 'UTC',
          ALTER COLUMN finished_at TYPE timestamptz USING finished_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE pipeline_runs
          ALTER COLUMN created_at TYPE timestamp USING created_at AT TIME ZONE 'UTC',
          ALTER COLUMN started_at TYPE timestamp USING started_at AT TIME ZONE 'UTC',
          ALTER COLUMN finished_at TYPE timestamp USING finished_at AT TIME ZONE 'UTC'
    """)

