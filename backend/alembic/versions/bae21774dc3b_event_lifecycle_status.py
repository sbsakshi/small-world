"""event lifecycle: started/awaiting_review statuses, rename completed to closed

Revision ID: bae21774dc3b
Revises: c133a1e4dd0a
Create Date: 2026-07-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bae21774dc3b'
down_revision: Union[str, None] = 'c133a1e4dd0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Completion is now driven by ground-truth actions (door check-in -> door close ->
    # lead's autopsy submission) instead of one manual staff click, so the old terminal
    # value's name no longer fits what it means.
    op.execute("ALTER TYPE event_status RENAME VALUE 'completed' TO 'closed'")
    op.execute("ALTER TYPE event_status ADD VALUE IF NOT EXISTS 'started'")
    op.execute("ALTER TYPE event_status ADD VALUE IF NOT EXISTS 'awaiting_review'")
    op.add_column('events', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Enum rename/add-value downgrade not supported for this revision")
