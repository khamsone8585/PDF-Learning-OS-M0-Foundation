"""Guarded UUID-owned storage for original PDFs and extracted page text."""
import fcntl
import os
import re
import stat
from pathlib import Path
from uuid import UUID

from app.services.library_errors import LibraryError

PAGE_FILE = re.compile(r'^[0-9]{6}\.txt$')


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


def safe_file(path):
    if path.is_symlink() or not path.is_file():
        raise OSError('Unsafe storage file')


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
        for area in ('books', '.staging', '.trash', '.processing'):
            path = root / area
            path.mkdir(exist_ok=True)
            safe_directory(path)

    def _validate_pages(self, pages):
        safe_directory(pages)
        for child in pages.iterdir():
            if not PAGE_FILE.fullmatch(child.name):
                raise OSError('Unknown extracted page entry')
            safe_file(child)

    def _validate_generation(self, generation):
        canonical_id(generation.name)
        safe_directory(generation)
        children = list(generation.iterdir())
        if len(children) != 1 or children[0].name != 'pages':
            raise OSError('Unknown extraction generation entry')
        self._validate_pages(children[0])

    def _validate_extracted(self, extracted):
        safe_directory(extracted)
        for generation in extracted.iterdir():
            self._validate_generation(generation)

    def _validate_book(self, path, area):
        safe_directory(path)
        allowed = {'original.pdf'} if area == '.staging' else {'original.pdf', 'extracted'}
        for child in path.iterdir():
            if child.name not in allowed or child.is_symlink():
                raise OSError('Unknown or unsafe book entry')
            if child.name == 'original.pdf':
                safe_file(child)
            else:
                self._validate_extracted(child)

    def _validate_processing_book(self, path):
        safe_directory(path)
        for attempt in path.iterdir():
            self._validate_generation(attempt)

    def path(self, area, book_id):
        canonical_id(book_id)
        if area not in ('books', '.staging', '.trash', '.processing'):
            raise OSError('Unknown area')
        safe_directory(self.root)
        safe_directory(self.root / area)
        path = self.root / area / book_id
        if path.is_symlink():
            raise OSError('Unsafe book directory')
        if path.exists():
            if area == '.processing':
                self._validate_processing_book(path)
            else:
                self._validate_book(path, area)
        return path

    def entries(self, area):
        safe_directory(self.root / area)
        try:
            return [self.path(area, child.name) for child in (self.root / area).iterdir()]
        except LibraryError as exc:
            raise OSError('Unknown storage entry') from exc

    def create_stage(self, book_id):
        for area in ('books', '.staging', '.trash'):
            if self.path(area, book_id).exists():
                raise FileExistsError('Book ID collision')
        path = self.path('.staging', book_id)
        path.mkdir(mode=0o700)
        return path

    def move(self, source, target, book_id):
        if source not in ('books', '.staging', '.trash') or target not in ('books', '.trash'):
            raise OSError('Invalid storage move')
        src, dst = self.path(source, book_id), self.path(target, book_id)
        if dst.exists():
            raise FileExistsError('Refusing overwrite')
        src.rename(dst)
        sync_directory(src.parent)
        sync_directory(dst.parent)

    def _remove_generation(self, generation):
        self._validate_generation(generation)
        pages = generation / 'pages'
        for page in pages.iterdir():
            page.unlink()
        pages.rmdir()
        generation.rmdir()

    def _remove_book(self, path, area):
        self._validate_book(path, area)
        (path / 'original.pdf').unlink(missing_ok=True)
        extracted = path / 'extracted'
        if extracted.exists():
            for generation in list(extracted.iterdir()):
                self._remove_generation(generation)
            extracted.rmdir()
        path.rmdir()

    def remove(self, area, book_id):
        if area not in ('books', '.staging', '.trash'):
            raise OSError('Invalid removal area')
        path = self.path(area, book_id)
        if path.exists():
            self._remove_book(path, area)
            sync_directory(path.parent)

    def available(self, book_id):
        return (self.path('books', book_id) / 'original.pdf').is_file()

    def create_processing(self, book_id, attempt_id):
        canonical_id(attempt_id)
        book = self.path('books', book_id)
        if not book.exists():
            raise FileNotFoundError('Book storage is missing')
        parent = self.path('.processing', book_id)
        if not parent.exists():
            parent.mkdir(mode=0o700)
        attempt = parent / attempt_id
        if attempt.exists():
            raise FileExistsError('Processing attempt collision')
        attempt.mkdir(mode=0o700)
        (attempt / 'pages').mkdir(mode=0o700)
        return attempt

    def finish_processing(self, book_id, attempt_id):
        canonical_id(attempt_id)
        parent = self.path('.processing', book_id)
        attempt = parent / attempt_id
        self._validate_generation(attempt)
        book = self.path('books', book_id)
        extracted = book / 'extracted'
        if extracted.exists():
            self._validate_extracted(extracted)
        else:
            extracted.mkdir(mode=0o700)
            sync_directory(book)
        target = extracted / attempt_id
        if target.exists():
            raise FileExistsError('Extraction generation collision')
        attempt.rename(target)
        sync_directory(parent)
        sync_directory(extracted)
        if not any(parent.iterdir()):
            parent.rmdir()
            sync_directory(self.root / '.processing')
        return target

    def generations(self, book_id):
        book = self.path('books', book_id)
        extracted = book / 'extracted'
        if not extracted.exists():
            return []
        self._validate_extracted(extracted)
        return list(extracted.iterdir())

    def generation(self, book_id, generation_id):
        canonical_id(generation_id)
        path = self.path('books', book_id) / 'extracted' / generation_id
        if path.exists():
            self._validate_generation(path)
        return path

    def remove_generation(self, book_id, generation_id):
        generation = self.generation(book_id, generation_id)
        if generation.exists():
            parent = generation.parent
            self._remove_generation(generation)
            if not any(parent.iterdir()):
                parent.rmdir()
                sync_directory(parent.parent)
            else:
                sync_directory(parent)

    def remove_processing(self, book_id, attempt_id=None):
        parent = self.path('.processing', book_id)
        if not parent.exists():
            return
        attempts = [parent / attempt_id] if attempt_id else list(parent.iterdir())
        for attempt in attempts:
            if attempt.exists():
                self._remove_generation(attempt)
        if not any(parent.iterdir()):
            parent.rmdir()
            sync_directory(parent.parent)
