"""Add M2 processing state, pages, and chapter structure."""
from alembic import op
import sqlalchemy as sa

revision = '0002_pdf_processing'
down_revision = '0001_books'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('books') as batch:
        batch.add_column(sa.Column('processing_status', sa.String(16), nullable=False,
                                   server_default='unprocessed'))
        batch.add_column(sa.Column('processing_error_code', sa.String(64)))
        batch.add_column(sa.Column('processing_error_message', sa.String(500)))
        batch.add_column(sa.Column('processing_started_at', sa.String(32)))
        batch.add_column(sa.Column('processed_at', sa.String(32)))
        batch.add_column(sa.Column('active_extraction_id', sa.String(36)))
        batch.add_column(sa.Column('toc_status', sa.String(16)))
        batch.create_check_constraint('valid_processing_status',
                                      "processing_status IN ('unprocessed', 'processing', 'processed', 'failed')")
        batch.create_check_constraint('valid_toc_status',
                                      "toc_status IS NULL OR toc_status IN ('available', 'partial', 'missing', 'invalid')")

    op.create_table(
        'pages',
        sa.Column('book_id', sa.String(36), sa.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('page_number', sa.Integer(), primary_key=True),
        sa.Column('char_count', sa.Integer(), nullable=False),
        sa.Column('text_sha256', sa.String(64), nullable=False),
        sa.CheckConstraint('page_number > 0', name='positive_page_number'),
        sa.CheckConstraint('char_count >= 0', name='nonnegative_char_count'),
        sa.CheckConstraint("length(text_sha256) = 64 AND text_sha256 NOT GLOB '*[^0-9a-f]*'",
                           name='valid_text_digest'),
    )
    op.create_table(
        'chapters',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('book_id', sa.String(36), sa.ForeignKey('books.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('start_page', sa.Integer(), nullable=False),
        sa.Column('end_page', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(16), nullable=False),
        sa.UniqueConstraint('book_id', 'position', name='uq_chapters_book_position'),
        sa.CheckConstraint('position >= 0', name='nonnegative_chapter_position'),
        sa.CheckConstraint('length(title) BETWEEN 1 AND 500', name='chapter_title_length'),
        sa.CheckConstraint('level > 0', name='positive_chapter_level'),
        sa.CheckConstraint('start_page > 0 AND end_page >= start_page', name='valid_chapter_range'),
        sa.CheckConstraint("source IN ('toc', 'fallback', 'manual')", name='valid_chapter_source'),
    )


def downgrade():
    op.drop_table('chapters')
    op.drop_table('pages')
    with op.batch_alter_table('books') as batch:
        batch.drop_constraint('valid_toc_status', type_='check')
        batch.drop_constraint('valid_processing_status', type_='check')
        batch.drop_column('toc_status')
        batch.drop_column('active_extraction_id')
        batch.drop_column('processed_at')
        batch.drop_column('processing_started_at')
        batch.drop_column('processing_error_message')
        batch.drop_column('processing_error_code')
        batch.drop_column('processing_status')
