from contextlib import asynccontextmanager

from starlette.formparsers import MultiPartException, MultiPartParser


class CompleteMultipartParser(MultiPartParser):
    """Reject truncated bodies, including a complete file with a missing final boundary.

    The pinned Starlette parser closes partial spools on exceptions, but its
    finalize() accepts truncation. Keep cleanup for that case here as well.
    """
    complete = False

    def on_end(self):
        self.complete = True

    async def parse(self):
        form = await super().parse()
        if not self.complete:
            # Includes the current unfinished file, which is not in FormData yet.
            for spool in self._files_to_close_on_error:
                spool.close()
            raise MultiPartException('Incomplete multipart body')
        return form


@asynccontextmanager
async def upload_form(request):
    parser = CompleteMultipartParser(request.headers, request.stream(),
                                     max_files=1, max_fields=4, max_part_size=4096)
    form = await parser.parse()
    try:
        yield form
    finally:
        # Close synchronously: cancellation must not abandon upload spools.
        for spool in parser._files_to_close_on_error:
            spool.close()
