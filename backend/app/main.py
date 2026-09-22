from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.body_limit import UploadBodyLimit
from app.api.books import router as books_router
from app.api.processing import router as processing_router
from app.api.health import router
from app.db.migrations import schema_ready
from app.services.library import Library
from app.services.library_errors import LibraryError, storage_error
from app.services.library_storage import DataLock
from app.services.processing import PDFProcessingService
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
    lock = None
    application.state.library = None
    application.state.processing = None
    application.state.library_error = storage_error()
    if engine is not None:
        try:
            lock = DataLock(database_path().parent)
            if not schema_ready(engine):
                raise LibraryError(503, 'library_setup_required',
                                   'Stop the backend, run python -m alembic upgrade head, then restart.')
            application.state.library = Library(engine, database_path().parent)
            application.state.processing = PDFProcessingService(application.state.library)
            application.state.library_error = None
        except LibraryError as exc:
            application.state.library_error = exc
        except (OSError, ValueError, SQLAlchemyError):
            pass
    try:
        yield
    finally:
        if lock is not None:
            lock.close()
        if engine is not None:
            engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title='PDF Learning OS', lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_credentials=False,
    )
    application.add_middleware(UploadBodyLimit)

    @application.exception_handler(LibraryError)
    async def library_error_handler(request, exc):
        return JSONResponse(exc.body, status_code=exc.status)

    application.include_router(router)
    application.include_router(books_router)
    application.include_router(processing_router)
    return application


app = create_app()
