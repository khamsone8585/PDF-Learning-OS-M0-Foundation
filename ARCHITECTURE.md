# ARCHITECTURE.md — PDF Learning OS V0.1

## Goal

Support:

`PDF → Structured Book → Analysis → Learning Path → Study → Mastery → Markdown`

without RAG/vector infrastructure in V0.1.

## High-Level Architecture

```text
React + TypeScript + Vite
        │ HTTP/JSON
        ▼
FastAPI
├── Library Service
├── PDF Processing Service
├── Book Analysis Service
├── Learning Path Service
├── Study Service
├── Mastery Service
├── Markdown Export Service
└── AI Provider Adapter
        │
        ├── SQLite
        └── Local Filesystem
```

## Frontend Direction

```text
frontend/src/
  app/
  components/
  features/
    library/
    processing/
    analysis/
    learning-path/
    reader/
    recall/
    mastery/
    export/
  api/
  types/
  styles/
```

## Backend Direction

```text
backend/app/
  main.py
  api/
  models/
  schemas/
  services/
    library.py
    pdf_processing.py
    book_analysis.py
    learning_path.py
    study.py
    mastery.py
    markdown_export.py
  ai/
    base.py
    provider.py
  db/
```

## Storage

SQLite:
- books
- chapters
- learning goals
- book roles
- study sessions
- learner responses
- quiz results
- mastery evidence
- progress

Filesystem:
- original PDFs
- extracted text artifacts
- Markdown exports

## PDF Processing

Use PyMuPDF:

`Validate → Metadata → TOC → Page Text → Chapter Mapping → Persist`

Image-only PDFs should report that OCR is required; do not silently generate poor extraction.

## AI Boundary

Provider-specific code must be isolated behind an interface such as:

```python
class AIProvider:
    analyze_book(...)
    compare_books(...)
    recommend_learning_path(...)
    translate_text(...)
    explain_text(...)
    generate_recall_questions(...)
    evaluate_explanation(...)
    generate_quiz(...)
```

## Grounding Contract

Book-dependent AI responses should preserve source scope: book, chapter, page range, and whether the answer is source-based or general knowledge.

## API Sketch

- `GET /health`
- `POST /books`
- `GET /books`
- `GET /books/{book_id}`
- `DELETE /books/{book_id}`
- `POST /books/{book_id}/process`
- `GET /books/{book_id}/chapters`
- `POST /learning-goals`
- `POST /analysis/book-profile`
- `POST /analysis/compare-books`
- `POST /analysis/learning-path`
- `GET /chapters/{chapter_id}`
- `POST /study/translate`
- `POST /study/explain`
- `POST /study/explain-back`
- `POST /study/recall`
- `POST /study/quiz`
- `GET /progress`
- `POST /mastery/evidence`
- `PATCH /mastery/{concept_id}`
- `POST /exports/study-plan`
- `POST /exports/book-profile`
- `POST /exports/chapter-notes`
- `POST /exports/progress`

## Testing

Backend: Pytest for extraction, mapping, ordering, mastery rules, exports, API validation.

Frontend: Vitest + React Testing Library for import flow, processing state, comparison, chapter navigation, source/generated separation, recall, quiz, mastery.

## Scope Stop Rule

Return to PLAN if implementation starts requiring vector DB, embeddings, RAG, distributed workers, multi-user auth, realtime collaboration, cloud architecture, or autonomous agents.

## M0 foundation decisions

M0 implements only a React app shell, a health API client, FastAPI's health route, and SQLAlchemy 2.x SQLite connectivity. The feature/service trees above describe later milestones and are not pre-created as stubs.

- Frontend tooling: npm, Vite, TypeScript, CSS, ESLint, Vitest, React Testing Library, and jsdom. Backend tooling: Python venv/pip, FastAPI, Uvicorn, SQLAlchemy, Pytest, and HTTPX for API tests. Lockfiles capture resolved dependencies.
- SQLite location: `PDF_LEARNING_DATA_DIR/learning_os.sqlite3`; default repository-root `data/`. Relative overrides resolve against the repository root. No domain schema or Alembic in M0.
- Database engine belongs to the application lifespan and is disposed at shutdown. Importing the application does not open or create a database. Initialization failures leave health available; restart after correcting initialization configuration.
- `GET /health` executes `SELECT 1`, returns HTTP 200 with `{"status":"ok","database":"ok"}`, or HTTP 503 with `{"status":"error","database":"unavailable"}` for storage failure.
- Frontend reads `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`), validates the health response, and displays loading/ready/unavailable. Requests time out at five seconds and are cancelled on unmount.
- Development uses loopback ports 5173/8000. CORS permits only localhost and 127.0.0.1 origins on port 5173, without credentials. This is an origin policy, not authentication.


## M1 local library decisions

M1 implements FR-001–005 only. PyMuPDF performs structural PDF validation, page access, page count and title/author inspection; it does not extract text, TOC, chapters, images, OCR, or analysis. Add Alembic and python-multipart alongside PyMuPDF; preserve existing dependency versions in the lockfile.

### Schema and setup

`books`: UUID string primary key; required title (1–500), normalized display filename (1–255), page_count (>0), UTC RFC3339 imported_at, size_bytes (1–104857600), unique lowercase SHA-256; nullable author (<=500), edition (<=100), year (1–9999). Stored paths derive from UUID, never the submitted filename. SHA-256 exists only for deterministic duplicate rejection, not content-addressed storage. No future domain fields/tables are added.

An explicit `python -m alembic upgrade head` from backend uses the same `PDF_LEARNING_DATA_DIR` resolution as the app. Revision `0001_books` creates books and Alembic's version table. Migration obtains the same data-directory OS lock as the app; run with the backend stopped. Neither startup nor tests use create_all. Tests migrate temporary databases. Library readiness requires the expected Alembic revision; /health remains the M0 connectivity-only contract.

### Ownership and recoverability

One macOS/Linux backend process holds `.library.lock` through its lifespan. A reentrant in-process lock serializes library operations. Database reads determine recovery; no file cleanup runs when the current schema/database is unavailable.

The service owns `books/<uuid>/original.pdf`, `.staging/<uuid>/original.pdf`, and `.trash/<uuid>/original.pdf` under the resolved data directory. UUIDs are generated by the backend and allocated exclusively. Paths must be canonical and contain only known regular files; symlinks, unknown entries and overwrite conflicts are rejected. Original bytes are never rewritten.

Import: normalize/validate fields, stage bounded bytes and hash, structurally inspect, check duplicate, insert/flush DB row, sync/move original to final location, commit. On failure, a fresh DB read distinguishes a rolled-back insert from uncertain successful commit before removing files. Cleanup failure blocks mutations until recovery succeeds.

Delete: move owned directory to trash, delete/commit row, remove trash. Missing originals are allowed. Rollback restores trash; uncertain commit is checked with a fresh DB read. Post-commit cleanup failure returns deletion_cleanup_pending; an explicit same-ID retry can finish it. Startup prevalidates managed entries, restores trash with a row, removes trash without a row, removes abandoned staging and final directories without rows. Unknown/conflicting entries stop recovery without overwrite. M1 creates no derived artifacts; future ownership changes require another migration/design decision.

### Import boundary and metadata

Exactly one multipart file plus optional title/author/edition/year. File limit 100 MiB; total received-body limit 101 MiB regardless of Content-Length. Multipart fields are bounded; spools close on completion, parsing error, truncation, or disconnect. Inspection rejects zero bytes/pages, non-PDF, parser failures, repaired documents, and all encryption (including empty-password encryption). Page objects are opened without rendering or extraction. Structural validation cannot guarantee future rendering/extraction succeeds. Image-only PDFs remain valid library items.

Submitted title/author override usable embedded values; absent title falls back to normalized filename stem. Blank fields are absent. Edition/year are manual or null; never infer publication year from creation/modification metadata. Byte-identical imports return 409 with the existing ID without changing metadata; same-name different files receive separate IDs.

### API and frontend

Routes stay in app/api/books.py; business decisions live in services/library.py, with dedicated storage and PDF inspection modules. POST /books returns 201 and Location; GET /books returns {books: [...]} sorted imported_at descending then id ascending; GET /books/{uuid} returns one book; DELETE /books/{uuid} returns empty 204. No pagination/filter/search or file-serving endpoints.

Book responses include id, title, original_filename, author, edition, year, page_count, imported_at, size_bytes, and computed file_available. Hashes and storage paths remain internal. Missing original files do not erase catalog entries.

Library errors use {error: {code, message}} with optional field/existing_book_id. Malformed multipart 400; limits 413; non-multipart 415; invalid fields/UUID/PDF 422; not found 404; duplicate 409; storage/schema/cleanup 503. Exceptions never leak paths, SQL or parser details. Allowed CORS methods are GET/POST/DELETE for the existing two loopback origins, without credentials.

The React library screen has import and optional fields, list/loading/empty/error/retry states, metadata details, missing-file warnings, duplicate navigation, and inline deletion confirmation. Cancel receives initial focus; results/errors are announced accessibly. Reads abort at 10 seconds, mutations at 120 seconds. Unknown mutation outcomes refresh the list and require an explicit retry; no optimistic deletion or mutation replay. Existing health behavior is independent.
