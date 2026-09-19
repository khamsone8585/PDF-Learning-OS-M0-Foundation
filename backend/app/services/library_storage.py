"""Only generated UUID directories and original.pdf are owned by M1."""
import fcntl
import os
import stat
from pathlib import Path
from uuid import UUID

from app.services.library_errors import LibraryError


def canonical_id(value):
    try:
        if str(UUID(value)) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    raise LibraryError(422, 'invalid_id', 'A canonical book UUID is required.', field='book_id')


def safe_directory(path):
    if path.is_symlink() or not path.is_dir():
        raise OSError('Unsafe storage directory')


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class DataLock:
    def __init__(self, root):
        self.fd = None
        root.mkdir(parents=True, exist_ok=True)
        safe_directory(root)
        fd = os.open(root / '.library.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError('Unsafe lock file')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class Storage:
    def __init__(self, root: Path):
        self.root = root
        for area in ('books', '.staging', '.trash'):
            path = root / area
            path.mkdir(exist_ok=True)
            safe_directory(path)

    def path(self, area, book_id):
        canonical_id(book_id)
        if area not in ('books', '.staging', '.trash'):
            raise OSError('Unknown area')
        safe_directory(self.root)
        safe_directory(self.root / area)
        path = self.root / area / book_id
        if path.is_symlink():
            raise OSError('Unsafe book directory')
        if path.exists():
            safe_directory(path)
            for child in path.iterdir():
                if child.name != 'original.pdf' or child.is_symlink() or not child.is_file():
                    raise OSError('Unknown or unsafe book entry')
        return path

    def entries(self, area):
        safe_directory(self.root / area)
        try:
            return [self.path(area, child.name) for child in (self.root / area).iterdir()]
        except LibraryError as exc:
            raise OSError('Unknown storage entry') from exc

    def create_stage(self, book_id):
        # Check all destinations before owning a new directory.
        for area in ('books', '.staging', '.trash'):
            if self.path(area, book_id).exists():
                raise FileExistsError('Book ID collision')
        path = self.path('.staging', book_id)
        path.mkdir(mode=0o700)
        return path

    def move(self, source, target, book_id):
        src, dst = self.path(source, book_id), self.path(target, book_id)
        if dst.exists():
            raise FileExistsError('Refusing overwrite')
        src.rename(dst)
        sync_directory(src.parent)
        sync_directory(dst.parent)

    def remove(self, area, book_id):
        path = self.path(area, book_id)
        if path.exists():
            (path / 'original.pdf').unlink(missing_ok=True)
            path.rmdir()
            sync_directory(path.parent)

    def available(self, book_id):
        return (self.path('books', book_id) / 'original.pdf').is_file()
