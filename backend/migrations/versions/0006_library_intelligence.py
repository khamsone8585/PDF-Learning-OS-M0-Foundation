"""Add library intelligence reviews and curriculum triage sessions."""
from alembic import op
import sqlalchemy as sa

revision = '0006_library_intelligence'
down_revision = '0005_book_comparisons'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'curriculum_triages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000)),
        sa.Column('target_domain', sa.String(200)),
        sa.Column('target_topics_json', sa.Text(), nullable=False),
        sa.Column('difficulty_ceiling', sa.String(16)),
        sa.Column('scope_kind', sa.String(20), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('scope_fingerprint', sa.String(64), nullable=False),
        sa.Column('input_fingerprint', sa.String(64), nullable=False),
        sa.Column('algorithm_version', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('applied_goal_id', sa.String(36),
                  sa.ForeignKey('learning_goals.id', ondelete='SET NULL'), unique=True),
        sa.Column('created_at', sa.String(32), nullable=False),
        sa.Column('updated_at', sa.String(32), nullable=False),
        sa.Column('applied_at', sa.String(32)),
        sa.CheckConstraint('length(title) BETWEEN 1 AND 200', name='triage_title_length'),
        sa.CheckConstraint('description IS NULL OR length(description) <= 2000',
                           name='triage_description_length'),
        sa.CheckConstraint('target_domain IS NULL OR length(target_domain) BETWEEN 1 AND 200',
                           name='triage_domain_length'),
        sa.CheckConstraint("difficulty_ceiling IS NULL OR difficulty_ceiling IN "
                           "('beginner','intermediate','advanced')", name='triage_difficulty'),
        sa.CheckConstraint("scope_kind IN ('library_snapshot','selected')", name='triage_scope'),
        sa.CheckConstraint("status IN ('draft','applied','archived','invalidated')",
                           name='triage_status'),
        sa.CheckConstraint('revision > 0', name='triage_positive_revision'),
        sa.CheckConstraint("length(scope_fingerprint)=64 AND scope_fingerprint NOT GLOB '*[^0-9a-f]*'",
                           name='triage_scope_fingerprint'),
        sa.CheckConstraint("length(input_fingerprint)=64 AND input_fingerprint NOT GLOB '*[^0-9a-f]*'",
                           name='triage_input_fingerprint'),
    )
    op.create_index('uq_curriculum_triages_single_draft', 'curriculum_triages', ['status'],
                    unique=True, sqlite_where=sa.text("status = 'draft'"))
    op.create_table(
        'curriculum_triage_books',
        sa.Column('triage_id', sa.String(36),
                  sa.ForeignKey('curriculum_triages.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('book_id', sa.String(36),
                  sa.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_table(
        'library_relation_reviews',
        sa.Column('left_book_id', sa.String(36),
                  sa.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('right_book_id', sa.String(36),
                  sa.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('preferred_book_id', sa.String(36),
                  sa.ForeignKey('books.id', ondelete='CASCADE')),
        sa.Column('note', sa.String(1000)),
        sa.Column('created_at', sa.String(32), nullable=False),
        sa.Column('updated_at', sa.String(32), nullable=False),
        sa.CheckConstraint('left_book_id < right_book_id', name='relation_sorted_pair'),
        sa.CheckConstraint("decision IN ('same_work','related_edition','distinct')",
                           name='relation_decision'),
        sa.CheckConstraint("(decision='same_work' AND preferred_book_id IS NOT NULL) OR "
                           "(decision<>'same_work' AND preferred_book_id IS NULL)",
                           name='relation_preferred_coherence'),
        sa.CheckConstraint('preferred_book_id IS NULL OR preferred_book_id=left_book_id OR '
                           'preferred_book_id=right_book_id', name='relation_preferred_member'),
        sa.CheckConstraint('note IS NULL OR length(note) <= 1000', name='relation_note_length'),
    )


def downgrade():
    op.drop_table('library_relation_reviews')
    op.drop_table('curriculum_triage_books')
    op.drop_index('uq_curriculum_triages_single_draft', table_name='curriculum_triages')
    op.drop_table('curriculum_triages')
