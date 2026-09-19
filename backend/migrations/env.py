from alembic import context
from app.config import database_path
from app.db.connection import create_database_engine
from app.models.book import Base
from app.services.library_storage import DataLock

if context.is_offline_mode():
    raise RuntimeError('Run migrations online against the configured local database.')
path = database_path()
lock = DataLock(path.parent)
engine = None
try:
    engine = create_database_engine(path)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
finally:
    if engine is not None:
        engine.dispose()
    lock.close()
