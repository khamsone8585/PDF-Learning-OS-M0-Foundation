from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.book import BookResponse, BooksResponse
from app.api.upload_form import upload_form
from app.services.library_errors import LibraryError, storage_error
from app.services.library_storage import canonical_id

router = APIRouter()


def library(request):
    error = request.app.state.library_error
    if error:
        raise error
    return request.app.state.library


async def invoke(function, *args):
    try:
        return await run_in_threadpool(function, *args)
    except (OSError, SQLAlchemyError) as exc:
        raise storage_error() from exc


@router.post('/books', response_model=BookResponse, status_code=201, openapi_extra={
    'requestBody': {'required': True, 'content': {'multipart/form-data': {'schema': {
        'type': 'object', 'required': ['file'], 'additionalProperties': False,
        'properties': {'file': {'type': 'string', 'format': 'binary'},
                       'title': {'type': 'string', 'maxLength': 500},
                       'author': {'type': 'string', 'maxLength': 500},
                       'edition': {'type': 'string', 'maxLength': 100},
                       'year': {'type': 'integer', 'minimum': 1, 'maximum': 9999}},
    }}}},
})
async def import_book(request: Request):
    service = library(request)
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'multipart/form-data':
        raise LibraryError(415, 'multipart_required', 'Use multipart/form-data to import a PDF.')
    try:
        async with upload_form(request) as form:
            items = list(form.multi_items())
            allowed = {'file', 'title', 'author', 'edition', 'year'}
            if any(k not in allowed for k, _ in items) or len({k for k, _ in items}) != len(items):
                raise LibraryError(422, 'invalid_fields', 'Supply one file and only the optional metadata fields.')
            upload = form.get('file')
            if not isinstance(upload, UploadFile) or any(
                not isinstance(v, str) for k, v in items if k != 'file'
            ):
                raise LibraryError(422, 'invalid_fields', 'Supply one PDF in the file field.')
            result = await invoke(service.import_book, upload, {k: v for k, v in items if k != 'file'})
            return JSONResponse(result, status_code=201, headers={'Location': f"/books/{result['id']}"})
    except MultiPartException as exc:
        if exc.message == 'Request body too large':
            raise LibraryError(413, 'request_too_large', 'Request must be at most 101 MiB.') from exc
        status = 422 if exc.message.startswith(('Too many', 'Part exceeded')) else 400
        raise LibraryError(status, 'invalid_multipart', 'Invalid multipart upload.') from exc
    except LibraryError:
        raise
    except (OSError, SQLAlchemyError) as exc:
        raise storage_error() from exc
    except (ValueError, KeyError) as exc:
        raise LibraryError(400, 'invalid_multipart', 'Invalid multipart upload.') from exc


@router.get('/books', response_model=BooksResponse)
async def list_books(request: Request):
    return await invoke(library(request).list_books)


@router.get('/books/{book_id}', response_model=BookResponse)
async def details(book_id: str, request: Request):
    return await invoke(library(request).details, canonical_id(book_id))


@router.delete('/books/{book_id}', status_code=204)
async def delete(book_id: str, request: Request):
    await invoke(library(request).delete, canonical_id(book_id))
    return Response(status_code=204)
