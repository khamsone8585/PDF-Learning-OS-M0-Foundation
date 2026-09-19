"""Bound received bytes before the multipart parser; its exception closes spools."""
from starlette.formparsers import MultiPartException

MAX_REQUEST_BYTES = 101 * 1024 * 1024


class UploadBodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/books':
            return await self.app(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get('body', b''))
            if total > MAX_REQUEST_BYTES:
                raise MultiPartException('Request body too large')
            return message

        await self.app(scope, bounded_receive, send)
