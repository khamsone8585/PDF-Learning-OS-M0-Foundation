# CHANGELOG.md — PDF Learning OS

Only record completed and verified work.

## Unreleased

### M5 — Book Comparison — 2026-09-22

- Added one reproducible comparison snapshot per learning goal, with captured goal/profile inputs, exact deterministic topic and prerequisite matching, difficulty comparisons, coverage/overlap facts, input fingerprints, optimistic revisions, and stale-state detection.
- Added explicit manual role, rationale, relevance, optional depth/practice, focus-topic, evidence-reference, and review-confirmation contracts with server-owned provenance. Clients cannot forge captured inputs, derived results, or provenance.
- Added `GET /learning-goals/{goal_id}/comparison` and complete atomic `PUT`, readiness issues for missing profiles/topics, inactive/stale/conflict handling, safe corrupt-storage behavior, and transactional cleanup of snapshots affected by book deletion.
- Added an accessible active-goal comparison interface with readiness links, overview and detailed facts, source labels, explicit unknowns, exact-matching limitations, create/edit/cancel/save, stale review with judgment carryover, invalid-reference feedback, responsive tables, and profile/selection/focus refresh behavior.
- Verified Alembic revision `0005_book_comparisons (head)` on fresh, repeated, and populated-M4 migrations, including exact schema constraints, ownership/cascades, rollback, and preservation of all M1–M4 data and artifacts. No M6+ schema exists.
- Verified 150 backend tests, 68 frontend tests, dependency consistency, lint, typecheck, production build, migration checks, concurrent/ambiguous updates, restart persistence, stale profile/selection inputs, reprocessing independence, deletion cleanup, and M1–M4 regressions.
- Verified the complete real HTTP and Google Chrome M5 workflows using isolated disposable data: comparison creation, all seven dimensions, manual classifications/rationales/provenance, validation preservation, backend/browser restart persistence, profile and selection staleness, explicit reviewed replacements through revision 3, keyboard/accessibility behavior, and unrelated-data integrity.
- No M5 defect required a TEST change. No learner data was modified. No AI provider, automatic classification, semantic matching, scoring, RAG, embeddings, vector database, dependency ordering, stages, chapter sequence, learning path, study plan, M6+, new dependency, commit, or push was introduced.

### M4 — Book Profiles — 2026-09-22

- Added one current global profile per book with domain, difficulty, prerequisites, main topics, theory/practice orientation, strengths, weaknesses, suggested use, UTC timestamps, and cascading book ownership.
- Added strict full-profile create/replace validation, deterministic ordered-list persistence, server-owned per-field provenance, explicit absent-profile responses, and manual editing independent of PDF processing or file availability.
- Added `GET /books/{book_id}/profile` and `PUT /books/{book_id}/profile`, plus an accessible book-details panel for absent/read/create/edit/cancel, provenance labels, validation, busy/error/success states, focus handling, and unknown-outcome reload.
- Verified Alembic revision `0004_book_profiles (head)` on fresh, repeated, and populated-M3 upgrades, including exact schema/constraints, cascade cleanup, and preservation of M1–M3 database rows and filesystem artifacts.
- Verified 116 backend tests, 52 frontend tests, dependency consistency, lint, typecheck, build, live HTTP restart persistence, atomic invalid-update handling, server-owned provenance, deletion cleanup, and unrelated M1–M3 data preservation.
- Verified the complete real-browser M4 lifecycle in Google Chrome with isolated disposable data: absent state, all-eight-field creation, reload persistence, full replacement, validation preservation, keyboard controls, deletion, and post-reload absence. No learner data was modified.
- No AI calls, automatic profile generation, comparison, overlap analysis, role classification, learning path, RAG, embeddings, M5+ behavior, new dependency, commit, or push was introduced during certification.

### M3 — Learning Goals — 2026-09-22

- Added one-active-goal persistence with bounded title and optional description, inactive history, UTC timestamps, and a cascading many-to-many association for 3–5 distinct existing books.
- Added atomic active-goal replacement, complete selected-book updates, explicit validation for invalid/duplicate/missing IDs, and protected deletion that prevents silently invalidating the active goal.
- Added `POST /learning-goals`, `GET /learning-goals/active`, and `PUT /learning-goals/{goal_id}/books`, plus an accessible browser flow for creation, active display, selection bounds, replacement, and starting a new goal.
- Verified Alembic revision `0003_learning_goals (head)` on fresh and populated-M2 databases, including repeated upgrade safety, exact constraints/indexes, and preservation of existing books, pages, chapters, metadata, and filesystem artifacts.
- Verified 98 backend tests, 43 frontend tests, dependency consistency, lint, typecheck, build, live API restart persistence, single-active history, invalid-selection handling, deletion integrity, and unrelated M2 processed-content preservation.
- Verified the complete real-browser M3 lifecycle in Google Chrome with isolated disposable data. No learner data was modified, no M4+ behavior or new dependency was added, and no commit or push was performed during certification.

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
