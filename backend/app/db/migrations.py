from pathlib import Path
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

REVISION = '0004_book_profiles'


def migration_config():
    return Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'))


def schema_ready(engine):
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_heads() == (REVISION,)
