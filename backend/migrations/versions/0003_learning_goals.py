"""Add active learning goals and their selected books."""
from alembic import op
import sqlalchemy as sa

revision = '0003_learning_goals'
down_revision = '0002_pdf_processing'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'learning_goals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000)),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.String(32), nullable=False),
        sa.Column('updated_at', sa.String(32), nullable=False),
        sa.CheckConstraint('length(title) BETWEEN 1 AND 200', name='learning_goal_title_length'),
        sa.CheckConstraint('description IS NULL OR length(description) <= 2000',
                           name='learning_goal_description_length'),
        sa.CheckConstraint('is_active IN (0, 1)', name='learning_goal_active_boolean'),
    )
    op.create_index('uq_learning_goals_single_active', 'learning_goals', ['is_active'],
                    unique=True, sqlite_where=sa.text('is_active = 1'))
    op.create_table(
        'learning_goal_books',
        sa.Column('goal_id', sa.String(36),
                  sa.ForeignKey('learning_goals.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('book_id', sa.String(36),
                  sa.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade():
    op.drop_table('learning_goal_books')
    op.drop_index('uq_learning_goals_single_active', table_name='learning_goals')
    op.drop_table('learning_goals')
