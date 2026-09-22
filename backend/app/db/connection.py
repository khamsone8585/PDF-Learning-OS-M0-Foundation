from pathlib import Path

from sqlalchemy import URL, create_engine, event, text
from sqlalchemy.engine import Engine


def create_database_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create('sqlite', database=str(path)),
        connect_args={'check_same_thread': False, 'timeout': 2},
    )

    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    return engine


def ping_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text('SELECT 1')).scalar_one()
