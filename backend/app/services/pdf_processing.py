import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pymupdf

from app.services.library_errors import LibraryError
from app.services.pdf_inspection import clean_text

MIN_DOCUMENT_CHARS = 50
MIN_PAGE_CHARS = 20


@dataclass(frozen=True)
class ChapterDraft:
    title: str
    level: int
    start_page: int
    end_page: int
    source: str


@dataclass(frozen=True)
class Extraction:
    pages: list[str]
    chapters: list[ChapterDraft]
    toc_status: str


def normalize_toc(raw_toc, page_count):
    if not raw_toc:
        return [ChapterDraft('Full document', 1, 1, page_count, 'fallback')], 'missing'
    accepted = []
    changed = False
    last_page = 0
    previous_level = 0
    for entry in raw_toc:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            changed = True
            continue
        raw_level, raw_title, page = entry[:3]
        if (isinstance(raw_level, bool) or not isinstance(raw_level, int) or
                isinstance(page, bool) or not isinstance(page, int) or
                not isinstance(raw_title, str)):
            changed = True
            continue
        title = clean_text(raw_title)
        if not title or len(title) > 500 or page < 1 or page > page_count or page < last_page:
            changed = True
            continue
        level = 1 if not accepted else max(1, min(raw_level, previous_level + 1))
        if level != raw_level or title != raw_title.strip():
            changed = True
        accepted.append([title, level, page])
        last_page = page
        previous_level = level
    if not accepted:
        return [ChapterDraft('Full document', 1, 1, page_count, 'fallback')], 'invalid'
    chapters = []
    for index, (title, level, start) in enumerate(accepted):
        following = next((candidate[2] for candidate in accepted[index + 1:]
                          if candidate[1] <= level), None)
        end = page_count if following is None else max(start, following - 1)
        chapters.append(ChapterDraft(title, level, start, end, 'toc'))
    return chapters, 'partial' if changed else 'available'


def machine_readable(pages):
    counts = [sum(character.isalnum() for character in page) for page in pages]
    return sum(counts) >= MIN_DOCUMENT_CHARS and max(counts, default=0) >= MIN_PAGE_CHARS


def extract_pdf(path: Path, expected_sha256: str, expected_page_count: int):
    digest = hashlib.sha256()
    try:
        with path.open('rb') as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise LibraryError(409, 'source_file_missing',
                           'The original PDF is missing. Restore it before processing.') from exc
    if digest.hexdigest() != expected_sha256:
        raise LibraryError(409, 'source_file_changed',
                           'The stored PDF no longer matches the imported original.')
    try:
        with pymupdf.open(path) as document:
            if (not document.is_pdf or document.needs_pass or document.is_encrypted or
                    (document.metadata or {}).get('encryption') or document.is_repaired):
                raise ValueError('Unusable source')
            if document.page_count != expected_page_count:
                raise LibraryError(409, 'source_file_changed',
                                   'The stored PDF no longer matches the imported original.')
            pages = [document.load_page(index).get_text('text', sort=False)
                     for index in range(document.page_count)]
            if document.is_repaired:
                raise ValueError('Repaired source')
            try:
                raw_toc = document.get_toc(simple=True)
            except Exception:
                raw_toc = [None]
    except LibraryError:
        raise
    except Exception as exc:
        raise LibraryError(422, 'extraction_failed',
                           'Text could not be extracted from this PDF.') from exc
    if not machine_readable(pages):
        raise LibraryError(422, 'ocr_required',
                           'This PDF needs OCR, which is not supported in V0.1.')
    chapters, toc_status = normalize_toc(raw_toc, expected_page_count)
    return Extraction(pages, chapters, toc_status)


def write_pages(attempt: Path, pages: list[str]):
    if len(pages) > 999999:
        raise LibraryError(422, 'extraction_failed', 'This PDF has too many pages to process.')
    records = []
    pages_path = attempt / 'pages'
    for number, text in enumerate(pages, 1):
        data = text.encode('utf-8')
        target = pages_path / f'{number:06d}.txt'
        with target.open('xb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        records.append((number, len(text), hashlib.sha256(data).hexdigest()))
    from app.services.library_storage import sync_directory
    sync_directory(pages_path)
    sync_directory(attempt)
    return records
