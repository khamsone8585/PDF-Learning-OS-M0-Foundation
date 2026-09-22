"""Persist reviewed goal-specific comparison snapshots."""
from alembic import op
import sqlalchemy as sa

revision = '0005_book_comparisons'
down_revision = '0004_book_profiles'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'book_comparisons',
        sa.Column('goal_id', sa.String(36), sa.ForeignKey('learning_goals.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('input_fingerprint', sa.String(64), nullable=False),
        sa.Column('algorithm_version', sa.String(32), nullable=False),
        sa.Column('snapshot_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(32), nullable=False),
        sa.Column('updated_at', sa.String(32), nullable=False),
        sa.CheckConstraint('revision > 0', name='comparison_positive_revision'),
        sa.CheckConstraint("length(input_fingerprint) = 64 AND input_fingerprint NOT GLOB '*[^0-9a-f]*'",
                           name='comparison_fingerprint'),
    )
    op.create_table(
        'book_comparison_books',
        sa.Column('goal_id', sa.String(36), sa.ForeignKey('book_comparisons.goal_id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('book_id', sa.String(36), sa.ForeignKey('books.id', ondelete='CASCADE'),
                  primary_key=True),
    )


def downgrade():
    op.drop_table('book_comparison_books')
    op.drop_table('book_comparisons')
