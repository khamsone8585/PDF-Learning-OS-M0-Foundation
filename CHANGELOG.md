# CHANGELOG.md — PDF Learning OS

Only record completed and verified work.

## Unreleased

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
