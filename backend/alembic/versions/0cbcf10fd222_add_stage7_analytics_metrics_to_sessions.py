"""add_stage7_analytics_metrics_to_sessions

Revision ID: 0cbcf10fd222
Revises: 41f9b491b314
Create Date: 2026-10-25 12:24:20.904097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cbcf10fd222'
down_revision: Union[str, Sequence[str], None] = '41f9b491b314'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add avg_pace_rpm, summary_metrics, and analytics indexes."""
    with op.batch_alter_table('exercise_sessions') as batch_op:
        batch_op.add_column(sa.Column('avg_pace_rpm', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('summary_metrics', sa.JSON(), nullable=True))
        batch_op.create_index('ix_exercise_sessions_athlete_started', ['athlete_id', 'started_at'])
        batch_op.create_index('ix_exercise_sessions_athlete_exercise', ['athlete_id', 'exercise_name'])


def downgrade() -> None:
    """Downgrade schema: remove Stage 7 analytics columns and indexes."""
    with op.batch_alter_table('exercise_sessions') as batch_op:
        batch_op.drop_index('ix_exercise_sessions_athlete_exercise')
        batch_op.drop_index('ix_exercise_sessions_athlete_started')
        batch_op.drop_column('summary_metrics')
        batch_op.drop_column('avg_pace_rpm')
