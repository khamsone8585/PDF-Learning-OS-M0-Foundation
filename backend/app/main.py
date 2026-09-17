from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router
from app.config import database_path
from app.db.connection import create_database_engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    engine = None
    try:
        engine = create_database_engine(database_path())
    except (OSError, ValueError, SQLAlchemyError):
        # Keep the health route available even when storage cannot initialize.
        pass
    application.state.database_engine = engine
    try:
        yield
    finally:
        if engine is not None:
            engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title='PDF Learning OS', lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
        allow_methods=['GET'],
        allow_credentials=False,
    )
    application.include_router(router)
    return application


app = create_app()
