"""First library schema; immutable revision independent of runtime models."""
from alembic import op
import sqlalchemy as sa

revision = '0001_books'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('books',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('author', sa.String(500)),
        sa.Column('edition', sa.String(100)),
        sa.Column('year', sa.Integer()),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('imported_at', sa.String(32), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.UniqueConstraint('sha256', name='uq_books_sha256'),
        sa.CheckConstraint('page_count > 0', name='positive_pages'),
        sa.CheckConstraint('size_bytes > 0 AND size_bytes <= 104857600', name='bounded_size'),
        sa.CheckConstraint('year IS NULL OR (year >= 1 AND year <= 9999)', name='valid_year'),
        sa.CheckConstraint('length(title) BETWEEN 1 AND 500', name='title_length'),
        sa.CheckConstraint('length(original_filename) BETWEEN 1 AND 255', name='filename_length'),
        sa.CheckConstraint('author IS NULL OR length(author) <= 500', name='author_length'),
        sa.CheckConstraint('edition IS NULL OR length(edition) <= 100', name='edition_length'),
        sa.CheckConstraint("length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'", name='valid_digest'),
    )


def downgrade():
    op.drop_table('books')
