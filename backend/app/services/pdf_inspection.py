import unicodedata
from pathlib import Path

import pymupdf

from app.services.library_errors import LibraryError


def clean_text(value):
    return unicodedata.normalize('NFC', ''.join(
        char for char in value if not unicodedata.category(char).startswith('C')
    )).strip()


def filename(value):
    value = clean_text((value or '').replace('\\', '/').rsplit('/', 1)[-1])
    if value in ('', '.', '..') or len(value) > 255:
        raise LibraryError(422, 'invalid_filename', 'Supply a filename of 1–255 characters.', field='file')
    return value


def metadata_fields(fields):
    result = {}
    for key, limit in [('title', 500), ('author', 500), ('edition', 100)]:
        value = fields.get(key, '').strip()
        if len(value) > limit or any(unicodedata.category(c).startswith('C') for c in value):
            raise LibraryError(422, 'invalid_field', f'{key.title()} is invalid or too long.', field=key)
        result[key] = value or None
    year = fields.get('year', '').strip()
    if year and (not year.isascii() or not year.isdigit() or not 1 <= int(year) <= 9999):
        raise LibraryError(422, 'invalid_field', 'Year must be between 1 and 9999.', field='year')
    result['year'] = int(year) if year else None
    return result


def inspect_pdf(path: Path):
    try:
        with pymupdf.open(path) as doc:
            if not doc.is_pdf:
                raise ValueError('Not PDF')
            if doc.needs_pass or doc.is_encrypted or (doc.metadata or {}).get('encryption'):
                raise LibraryError(422, 'encrypted_pdf', 'Encrypted PDFs are not supported.')
            if doc.is_repaired or doc.page_count < 1:
                raise ValueError('Invalid structure')
            metadata = doc.metadata or {}
            for number in range(doc.page_count):
                doc.load_page(number)
            if doc.is_repaired:
                raise ValueError('Repaired structure')
            result = {'page_count': doc.page_count}
            for key in ('title', 'author'):
                value = clean_text(metadata.get(key) or '')
                result[key] = value if 0 < len(value) <= 500 else None
            return result
    except LibraryError:
        raise
    except Exception as exc:
        raise LibraryError(422, 'invalid_pdf', 'The selected file is not a usable PDF.') from exc
