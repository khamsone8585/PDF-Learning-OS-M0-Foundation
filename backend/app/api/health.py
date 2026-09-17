from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.connection import ping_database

router = APIRouter()


@router.get('/health')
def health(request: Request) -> JSONResponse:
    engine = request.app.state.database_engine
    if engine is not None:
        try:
            ping_database(engine)
            return JSONResponse({'status': 'ok', 'database': 'ok'})
        except (SQLAlchemyError, OSError):
            pass
    return JSONResponse(
        {'status': 'error', 'database': 'unavailable'}, status_code=503,
    )
