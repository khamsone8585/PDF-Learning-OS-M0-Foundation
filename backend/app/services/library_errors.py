class LibraryError(Exception):
    def __init__(self, status, code, message, **details):
        super().__init__(message)
        self.status = status
        self.body = {'error': {'code': code, 'message': message, **details}}


def storage_error():
    return LibraryError(503, 'library_storage_unavailable',
                        'Library storage is unavailable. Check local storage and restart the backend.')
