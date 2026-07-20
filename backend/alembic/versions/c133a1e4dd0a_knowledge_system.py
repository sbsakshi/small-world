"""knowledge system: event autopsies, decisions, issues

Revision ID: c133a1e4dd0a
Revises: d00c615dab00
Create Date: 2026-07-20 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c133a1e4dd0a'
down_revision: Union[str, None] = 'd00c615dab00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # volunteer_assignments gains a staff-only rating, written through from the autopsy form.
    op.add_column('volunteer_assignments', sa.Column('rating', sa.Integer(), nullable=True))

    # --- event_autopsies supersedes event_reports. The old table's freeform note/tags has no
    # honest mapping onto structured attendance/rating fields, so it isn't data-migrated; its
    # only row in any known environment is untouched dev scratch data. ---
    op.create_table(
        'event_autopsies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('submitted_by', sa.Integer(), nullable=False),
        sa.Column('attendance_actual', sa.Integer(), nullable=False),
        sa.Column('venue_rating', sa.Integer(), nullable=False),
        sa.Column('what_worked', sa.Text(), nullable=False),
        sa.Column('what_didnt', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id']),
        sa.ForeignKeyConstraint(['submitted_by'], ['staff.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.drop_table('event_reports')

    # --- decisions: rebuilt with FK tags + no status workflow. Existing rows are migrated
    # forward: `text` becomes both a truncated title and the full body; decided_at falls back
    # to the row's created_at date since the old schema never recorded a separate decided date;
    # staff_only has no equivalent (decisions are readable by all staff in the new model). ---
    op.execute('ALTER SEQUENCE decisions_id_seq RENAME TO decisions_legacy_id_seq')
    op.rename_table('decisions', 'decisions_legacy')
    op.create_table(
        'decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.Integer(), nullable=True),
        sa.Column('venue_id', sa.Integer(), nullable=True),
        sa.Column(
            'category',
            postgresql.ENUM('art', 'social', 'wellness', 'cooking', name='event_category', create_type=False),
            nullable=True,
        ),
        sa.Column('decided_at', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['staff.id']),
        sa.ForeignKeyConstraint(['city_id'], ['cities.id']),
        sa.ForeignKeyConstraint(['venue_id'], ['venues.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        """
        INSERT INTO decisions (id, title, body, author_id, city_id, venue_id, category,
                                decided_at, created_at, updated_at)
        SELECT id, left(text, 255), text, raised_by_id, city_id, venue_id, NULL,
               created_at::date, created_at, updated_at
        FROM decisions_legacy
        """
    )
    op.execute(
        """
        DO $$
        DECLARE max_id integer;
        BEGIN
            SELECT MAX(id) INTO max_id FROM decisions;
            IF max_id IS NOT NULL THEN
                PERFORM setval(pg_get_serial_sequence('decisions', 'id'), max_id);
            END IF;
        END $$;
        """
    )
    op.drop_table('decisions_legacy')
    op.execute('DROP SEQUENCE IF EXISTS decisions_legacy_id_seq')
    op.execute('DROP TYPE IF EXISTS decision_status')

    # --- issues: rebuilt with an escalation ladder instead of priority/due_date. Existing rows
    # are migrated forward: raised_by_type defaults to 'staff' (the only raiser type the old
    # schema supported), current_level defaults to 'city_lead' (where these all lived before —
    # there is no way to recover the true historical level), and resolution_note has no source
    # (the old schema never captured one for resolved issues). `status` is reused as-is: the
    # existing `issue_status` enum type already has exactly open/resolved. ---
    op.execute('ALTER SEQUENCE issues_id_seq RENAME TO issues_legacy_id_seq')
    op.rename_table('issues', 'issues_legacy')
    op.create_table(
        'issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('raised_by_type', sa.Enum('staff', 'volunteer', name='raised_by_type'), nullable=False),
        sa.Column('raised_by_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('venue_id', sa.Integer(), nullable=True),
        sa.Column('volunteer_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM('open', 'resolved', name='issue_status', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'current_level',
            sa.Enum('event_lead', 'city_lead', 'founder', name='issue_level'),
            nullable=False,
        ),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id']),
        sa.ForeignKeyConstraint(['venue_id'], ['venues.id']),
        sa.ForeignKeyConstraint(['volunteer_id'], ['volunteers.id']),
        sa.ForeignKeyConstraint(['resolved_by'], ['staff.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        """
        INSERT INTO issues (id, title, body, raised_by_type, raised_by_id, event_id, venue_id,
                             volunteer_id, status, current_level, resolution_note, resolved_by,
                             created_at, resolved_at)
        SELECT id, left(text, 255), text, 'staff', raised_by_id, NULL, venue_id, NULL,
               status, 'city_lead', NULL, resolved_by_id, created_at, resolved_at
        FROM issues_legacy
        """
    )
    op.execute(
        """
        DO $$
        DECLARE max_id integer;
        BEGIN
            SELECT MAX(id) INTO max_id FROM issues;
            IF max_id IS NOT NULL THEN
                PERFORM setval(pg_get_serial_sequence('issues', 'id'), max_id);
            END IF;
        END $$;
        """
    )
    op.drop_table('issues_legacy')
    op.execute('DROP SEQUENCE IF EXISTS issues_legacy_id_seq')
    op.execute('DROP TYPE IF EXISTS issue_priority')


def downgrade() -> None:
    raise NotImplementedError("Data-migrating downgrade not supported for the knowledge system revision")
