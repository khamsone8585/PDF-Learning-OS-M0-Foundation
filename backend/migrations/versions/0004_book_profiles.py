"""Add manually maintained book profiles."""
from alembic import op
import sqlalchemy as sa

revision = '0004_book_profiles'
down_revision = '0003_learning_goals'
branch_labels = None
depends_on = None

SOURCES = "'manual', 'ai_generated', 'ai_assisted', 'derived'"


def upgrade():
    op.create_table(
        'book_profiles',
        sa.Column('book_id', sa.String(36),
                  sa.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('domain', sa.String(200)),
        sa.Column('difficulty', sa.String(16)),
        sa.Column('prerequisites_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('main_topics_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('orientation', sa.String(20)),
        sa.Column('strengths_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('weaknesses_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('suggested_use', sa.Text()),
        sa.Column('domain_source', sa.String(16)),
        sa.Column('difficulty_source', sa.String(16)),
        sa.Column('prerequisites_source', sa.String(16)),
        sa.Column('main_topics_source', sa.String(16)),
        sa.Column('orientation_source', sa.String(16)),
        sa.Column('strengths_source', sa.String(16)),
        sa.Column('weaknesses_source', sa.String(16)),
        sa.Column('suggested_use_source', sa.String(16)),
        sa.Column('created_at', sa.String(32), nullable=False),
        sa.Column('updated_at', sa.String(32), nullable=False),
        sa.CheckConstraint('domain IS NULL OR length(domain) BETWEEN 1 AND 200',
                           name='book_profile_domain_length'),
        sa.CheckConstraint("difficulty IS NULL OR difficulty IN ('beginner', 'intermediate', 'advanced')",
                           name='book_profile_difficulty'),
        sa.CheckConstraint("orientation IS NULL OR orientation IN ('theory_heavy', 'balanced', 'practice_heavy')",
                           name='book_profile_orientation'),
        sa.CheckConstraint('suggested_use IS NULL OR length(suggested_use) BETWEEN 1 AND 2000',
                           name='book_profile_suggested_use_length'),
        *[sa.CheckConstraint(f'{field}_source IS NULL OR {field}_source IN ({SOURCES})',
                             name=f'book_profile_{field}_source')
          for field in ('domain', 'difficulty', 'prerequisites', 'main_topics', 'orientation',
                        'strengths', 'weaknesses', 'suggested_use')],
        *[sa.CheckConstraint(
            f'({field} IS NULL AND {field}_source IS NULL) OR '
            f'({field} IS NOT NULL AND {field}_source IS NOT NULL)',
            name=f'book_profile_{field}_source_coherence')
          for field in ('domain', 'difficulty', 'orientation', 'suggested_use')],
        *[sa.CheckConstraint(
            f"({field}_json = '[]' AND {field}_source IS NULL) OR "
            f"({field}_json <> '[]' AND {field}_source IS NOT NULL)",
            name=f'book_profile_{field}_source_coherence')
          for field in ('prerequisites', 'main_topics', 'strengths', 'weaknesses')],
    )


def downgrade():
    op.drop_table('book_profiles')
