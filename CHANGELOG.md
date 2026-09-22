# CHANGELOG.md — PDF Learning OS

Only record completed and verified work.

## Unreleased

### M2 — PDF Processing — 2026-09-22

- Added exact per-page PyMuPDF text extraction with immutable UTF-8 artifacts, 1-based physical page references, source digest validation, and durable processing/error state.
- Added deterministic PDF bookmark normalization and inclusive chapter mapping, explicit fallback structure, atomic manual fallback correction, and clear OCR-required handling without adding OCR.
- Added versioned extraction generations, SQLite page/chapter manifests with cascade ownership, restart recovery, safe reprocessing, and deletion cleanup for original and derived content.
- Added the accessible browser processing panel with processing/reprocessing status, nested outlines, page ranges, persistent errors, and fallback correction controls.
- Verified Alembic revision `0002_pdf_processing (head)`, 82 backend tests, 32 frontend tests, dependency consistency, lint, typecheck, build, exact extraction bytes/hashes, live restart/deletion recovery, and isolated storage integrity.
- Verified the real-browser M2 lifecycle in Google Chrome with disposable data: nested TOC, reprocessing, fallback correction and reload persistence, OCR-required behavior, deletion refresh/restart persistence, old-record 404 responses, and unrelated-data isolation. No learner data was modified.
- No OCR, AI, reader, M3+, task queue, cloud infrastructure, new dependency, commit, or push was introduced during certification.

### M1 — Local PDF Library — 2026-09-19

- Added local PDF import with byte-identical filesystem storage, optional bibliographic metadata, structural PDF validation, a 100 MiB file limit, and deterministic list and details APIs.
- Added the versioned Alembic `books` schema, UUID-owned storage, duplicate-content rejection, guarded import/delete compensation, startup recovery, single-process locking, and safe missing-file reporting.
- Added the accessible browser library flow for import, list, details, duplicate navigation, explicit delete confirmation, mutation uncertainty, missing files, and retry states while preserving the M0 health contract.
- Verified 64 backend tests, 28 frontend tests, frontend lint/typecheck/build, dependency consistency, fresh and repeated migrations, live HTTP import/restart/delete behavior, byte-identical persistence, CORS and storage isolation.
- Verified the complete real-browser lifecycle in Google Chrome with disposable PDF data in an isolated temporary learner directory: empty state, import/loading, metadata details, duplicate rejection, delete confirmation and cancellation, reload absence, backend-restart persistence, and final cleanup. Safari also confirmed the initial Ready and empty-library state.
- No M2 extraction, TOC, OCR, AI, learning, authentication, cloud, or multi-user behavior was added. Seven non-failing upstream Starlette, AnyIO, and PyMuPDF warnings remain.

### M0 — Repository Foundation — 2026-09-17

- Added the React/TypeScript/Vite app shell with accessible local health states, timeout handling, and restricted local API configuration.
- Added FastAPI `GET /health` with SQLAlchemy 2.x/SQLite connectivity, safe failure responses, and local CORS restrictions; no domain tables.
- Added isolated backend tests, frontend health-state tests, dependency locks, local-data ignore rules, and development documentation.
- Verified lint, build, typecheck, 11 frontend tests and 13 backend tests (zero failures), live HTTP health/CORS checks, and real Safari ready/unavailable/recovery behavior.
- No PDF, AI, learning, or M1+ features included. Git status/diff unavailable because the workspace is not initialized as a Git repository.
