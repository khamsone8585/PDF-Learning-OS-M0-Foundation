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
    goals/
    profiles/
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
- book profiles
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
- `GET /learning-goals/active`
- `PUT /learning-goals/{goal_id}/books`
- `GET /books/{book_id}/profile`
- `PUT /books/{book_id}/profile`
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

## M3 learning-goal decisions

M3 implements FR-012–013 only. `learning_goals` stores UUID, bounded title and optional description, active state, and UTC created/updated timestamps. `learning_goal_books` is a cascading many-to-many association with a composite primary key. A SQLite partial unique index permits at most one active goal.

Creating a goal requires 3–5 distinct existing books and atomically deactivates the prior active goal. Inactive goals are retained as read-only history; M3 has no drafts, history UI, reactivation, deletion, or title/description editing. The active goal's complete selection may be replaced with another valid 3–5-book set. Book processing state does not affect selection.

Goal mutations share the library lock with import, processing, correction, and deletion. Deletion is rejected while a book belongs to the active goal, so the active selection cannot silently become invalid. Associations belonging only to inactive goals cascade when their book is deleted.

## M4 book-profile decisions

M4 implements FR-014–015 only. `book_profiles` stores zero or one current global profile per book, using `book_id` as both primary key and cascading foreign key. It stores domain, difficulty, prerequisites, main topics, theory/practice orientation, strengths, weaknesses, suggested use, UTC created/updated timestamps, and one nullable provenance value per profile field. Ordered lists use deterministic JSON arrays in SQLite text columns and arrays in API responses.

Profiles are manually maintained in M4. A complete `PUT /books/{book_id}/profile` creates or replaces the current profile and `GET /books/{book_id}/profile` returns either that profile or an explicit null profile for an existing book. At least one field must be populated. The API does not accept provenance; populated values are marked `manual` and empty values have null provenance. There is no history, PATCH, profile deletion, goal-specific profile, analysis endpoint, or M5 comparison/role behavior.

Profile mutations share the library lock with import, processing, goal mutation, and deletion. Profiling does not depend on processing state, local-file availability, extracted text, or AI. Book deletion relies on the database foreign-key cascade to remove the profile without changing filesystem cleanup behavior.

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


## M2 PDF processing decisions

M2 implements FR-006–011 only. Processing is synchronous in the existing FastAPI threadpool and uses PyMuPDF 1.28.2. No OCR, AI, reader, search, task queue, or new dependency is introduced.

### State and schema

Books persist `unprocessed`, `processing`, `processed`, or `failed`, safe error code/message, attempt/start and last-success timestamps, active extraction UUID, and TOC status. `has_processed_content` is computed from the active generation, so a failed reprocess can retain the prior successful content. Startup changes abandoned processing attempts to `failed / processing_interrupted`.

`pages` stores the book UUID, 1-based physical PDF page number, exact-text character count, and artifact SHA-256. `chapters` stores ordered UUID rows with title, normalized hierarchy level, inclusive page range, and `toc`, `fallback`, or `manual` source. Foreign keys cascade on confirmed book deletion and SQLite foreign-key enforcement is enabled on every connection.

### Extraction and source integrity

Before processing, the stored original must match the M1 SHA-256 and page count and remain structurally valid, unencrypted, and unrepaired. Each page uses `get_text("text", sort=False)`. The returned string is encoded directly as UTF-8 without trimming, Unicode normalization, sorting, rewriting, or AI transformation. Page artifacts are immutable and named by physical page number.

A document is machine-readable only when extraction contains at least 50 Unicode letters/digits overall and one page contains at least 20. Otherwise processing fails with `ocr_required`; OCR is explicitly unsupported in V0.1. Empty individual pages remain valid when the document-level rule passes.

TOC entries are validated in source order. Invalid, out-of-range, and backward entries are skipped; the first valid level becomes 1 and deeper jumps are clamped to one level. Inclusive ranges end before the next same-or-shallower entry. TOC status is available, partial, missing, or invalid. No usable TOC creates one labeled `Full document` fallback rather than invented chapters.

Fallback/manual structure can be replaced atomically with flat titled sections whose first page is 1 and subsequent starts strictly increase. TOC-derived structure is read-only in M2. Successful reprocessing preserves a manual correction; generated TOC/fallback structure is regenerated.

### Storage and recovery

Extracted text is filesystem data, while SQLite is its structural manifest:

```text
.processing/<book-uuid>/<attempt-uuid>/pages/000001.txt
books/<book-uuid>/extracted/<generation-uuid>/pages/000001.txt
```

An attempt writes, flushes, and syncs all page files before its directory moves to the final UUID generation. One database transaction replaces page/generated-chapter rows and switches the active generation. The old generation remains available until that commit. A fresh database read resolves ambiguous commits; startup removes abandoned attempts and unreferenced generations only after validating every managed entry. Missing active artifacts become a safe failed state. Symlinks, unknown entries, and conflicting layouts stop recovery without deletion.

M1 trash operations move the complete UUID directory, so original and extracted data share deletion rollback/recovery. A post-commit cleanup failure retains the valid active generation, reports `processing_cleanup_pending`, and blocks mutations until recovery succeeds.

### API and frontend

`POST /books/{id}/process` returns the terminal Book response; `GET /books/{id}/chapters` returns processing/TOC/source state and the ordered outline; `PUT /books/{id}/chapters` replaces fallback/manual sections. Book list/details include status, safe error, timestamps, content availability, and TOC status. Hashes, generation IDs, paths, and page text are not exposed.

The library detail panel shows processing/reprocessing, durable failure and OCR-required messages, an indented outline with page ranges, and a flat fallback correction editor. It polls a server-side processing state every two seconds, bounds processing requests at ten minutes, and refreshes unknown outcomes without automatic replay. Chapter text reading remains M7.

## M5 book-comparison decisions

M5 implements FR-016–018 with profile inputs, deterministic matching, and explicit learner judgments only. `BookComparisonService` shares the library lock with goal/profile mutations and deletion. Thin GET/PUT routes live at `/learning-goals/{goal_id}/comparison`. No PDF text, page files, chapters, TOCs, processing status, AI service, or external provider participates in comparison.

An editable preview requires an active goal with 3–5 existing selected books, each having an M4 profile and at least one nonblank main topic. Missing profiles/topics yield per-book readiness issues; optional missing facts remain unknown. Empty prerequisites mean not recorded, not absence of prerequisites. Inactive goals can return saved snapshots but cannot be edited.

`profile_exact_v1` collapses Unicode whitespace, trims, and casefolds topic/prerequisite labels. Matching is exact thereafter: punctuation, acronyms, synonyms and translations are not reconciled. Originals and M4 field provenance remain captured unchanged. Sorted book UUIDs and topic keys stabilize coverage, unique-listed topics, and all unordered pairs. Pairs contain topic intersection/differences, ordinal difficulty comparison, and prerequisite intersection/differences (unknown if either list is empty). Ordering is not a study sequence; coverage is not completeness, quality, or depth.

Each saved book has one explicit `core`, `selected_chapters`, `reference`, or `skip_for_now` role; a trimmed 1–2,000-character rationale; relevance (`high`, `partial`, `low`, `unknown`) with a 1–1,000-character explanation; nullable depth (`overview`, `working_detail`, `deep_treatment`) and practice (`limited`, `some`, `substantial`) assessments with explanations; up to 50 unique canonical focus-topic keys; up to 20 unique evidence references; and `reviewed: true`. SELECTED CHAPTERS requires at least one own topic but does not select chapters. No CORE book is required and no role is inferred. Practice assessment is not inferred from orientation; depth is not inferred from difficulty.

Evidence shapes are `{kind: "profile_field", field}`, `{kind: "topic", topic}`, or `{kind: "pair", other_book_id, dimension}` where dimension is overlap, difficulty, or prerequisites. Targets must be populated own fields/topics or known pair facts involving this book. Evidence is optional; manual explanations remain unverified learner statements, never purported PDF evidence. Server-owned provenance distinguishes captured M4 facts, derived matches with algorithm/source references, and manual judgments. Strict requests reject unknown fields, including client provenance, snapshots, or computed results.

Alembic `0005_book_comparisons` adds only `book_comparisons` and `book_comparison_books`. One parent row per goal stores a positive revision, SHA-256 input fingerprint, algorithm version, typed snapshot JSON, and UTC creation/update timestamps. The composite-key membership table cascades from comparison and book. Snapshots capture goal context, selection/titles, full profiles/provenance/timestamps, comparison output, and reviewed judgments. M4 remains authoritative for current facts; there is no snapshot history or persisted draft.

Fingerprints hash canonical JSON of current goal context/update timestamp, sorted selection, titles, complete profiles/provenance/update timestamps, and algorithm version. GET compares this with the saved fingerprint without writing. Profile/selection edits (including timestamp-only edits) conservatively stale the snapshot; reprocessing does not. Saved data stays readable when stale or unready. PUT recomputes readiness/token, checks `expected_revision` (null means no snapshot), validates exact selected membership/references, and atomically replaces the snapshot and membership rows. Conflicts return specific 409 codes; malformed submissions return 422; missing goals return 404; corrupt stored data returns the safe storage 503.

Book deletion first applies the existing active-goal guard. In the existing deletion transaction it deletes all comparison parents containing that book before deleting the book; membership cascades and rollback covers comparisons and book state together. Deleting a book intentionally discards affected judgments, including inactive-goal snapshots. Unrelated snapshots remain unchanged.

The active-goal feature owns the comparison panel locally. It loads on demand, goal updates, profile-save signals, explicit refresh, and window focus. Current facts and saved stale facts are labeled separately. Reviewing current inputs carries judgments by book ID, resets every review confirmation, starts new books unclassified, excludes removed books, and flags obsolete topics/references. Drafts survive server errors and unknown outcomes; authoritative reload never replays PUT or silently replaces drafts. Shared library busy handling, native labeled controls, accessible tables/stacked narrow-screen rows, status/errors, and focus restoration are retained.

M6 may consume only a ready, nonstale saved active-goal comparison: goal/books, captured profiles/provenance, deterministic facts, manual assessments/roles/rationales/focus topics, revision/fingerprint/algorithm. M5 supplies no chapter IDs, ordering, dependencies, stages, schedules, or study-plan artifact.

## M5.5 library-intelligence and curriculum-triage decisions

M5.5 implements FR-048–052 without changing M3's 3–5-book learning-goal invariant or M5's reviewed-comparison contract. Library intelligence reads only M1 display metadata and M4 profile values/provenance. It never reads PDF bytes, extracted pages, TOCs, or chapters, and processing state is informational only. The feature remains deterministic and manual-first: there is no AI provider, semantic matching, score, background worker, cache, graph database, RAG, or embedding.

`profile_matching.py` owns the Unicode-whitespace collapse, trim, and casefold primitives shared with M5. `profile_exact_v1` uses exact normalized topic, prerequisite, and domain keys. `bibliographic_exact_v1` groups exact normalized title plus nonblank author; conflicting explicit edition or year identifies a related-edition candidate, otherwise a probable duplicate. Topic relationships are generated through an inverted index only for pairs sharing a recorded key. Equivalent and subset relations require at least two shared keys. These labels describe recorded profile facts, not semantic equivalence, completeness, quality, or a deletion recommendation.

The on-demand library map batches books and profiles, builds its indexes once, and returns readiness, compact profile facts, group counts, unique topics, and separate bibliographic/topic/prerequisite relationship counts. Relationship and prerequisite APIs are stably ordered and paginated at no more than 100 rows. M1's private SHA-256 continues to reject exact content duplicates at import and is never returned. Explicit prerequisite-provider edges match a prerequisite to another candidate's main topic or domain exactly; unresolved requirements and multiple providers remain visible and do not imply study order.

Alembic `0006_library_intelligence` adds `curriculum_triages`, `curriculum_triage_books`, and `library_relation_reviews`. A partial unique index allows one draft. Candidate membership and relation-review pairs use cascading book foreign keys; pairs are UUID-sorted and `same_work` requires a preferred member. Triage rows retain bounded intent, target topics, optional domain/ceiling, snapshot scope, positive revision, accepted scope/input fingerprints, algorithm version, lifecycle state, optional applied-goal link, and UTC timestamps. Applied sessions are read-only history; a replacement draft archives the existing draft only inside the successful replacement transaction.

Whole-library scope captures the current book IDs and becomes stale after an import or deletion until a complete update explicitly synchronizes it. Selected scope ignores unrelated imports and becomes stale when a member disappears. Profile changes and applicable pair-review changes alter the input token; processing and M5 comparison changes do not. A deletion cascades draft membership, invalidates affected applied triage history, removes applicable relation reviews, and preserves the existing active-goal deletion guard and M5 comparison cleanup transaction.

`curriculum_triage_v1` labels each candidate from exact evidence as direct, foundation, supporting, no recorded match, insufficient data, or above the optional ceiling. It greedily covers target topics, adds exact prerequisite providers for selected direct books, fills only from supported candidates, uses orientation/unique-topic evidence for optional fourth or fifth books, excludes nonpreferred reviewed same-work copies, and never auto-selects both sides of an unreviewed probable-duplicate pair. Results contain no numeric score or study sequence. Fewer than three supported candidates produce a partial recommendation rather than unrelated padding.

Confirmation requires a current token/revision, explicit recommendation review, exactly 3–5 distinct ready current candidates, complete M5 judgments, at least one CORE or SELECTED role, and no LATER role. Under the shared library lock, one SQLite transaction deactivates the old active goal, creates the new M3 goal, validates/builds revision 1 of the M5 snapshot with server-owned provenance, records exact comparison membership, and marks the triage applied. Any conflict or validation/storage failure rolls back the complete handoff.

Thin routes expose `GET /library-intelligence/map`, paginated `GET /library-intelligence/relations`, paginated `GET /library-intelligence/prerequisites`, strict `PUT /library-intelligence/relation-reviews`, and create/list/get/replace/confirm operations under `/curriculum-triages`. The React library screen owns a collapsible map, filters, profile-readiness queue, paginated evidence review, draft/history navigation, deterministic shortlist, manual override, and complete confirmation editor. Native controls, status/error regions, focus handling, stale warnings, and unknown-outcome reload without mutation replay preserve the established frontend conventions.

M6 receives only the active 3–5-book M3 goal, its current reviewed M5 snapshot, and M5.5's exact prerequisite-provider context for those selected books. M5.5 adds no path ordering, stage, chapter selection, dependency sequence, schedule, or study-plan artifact.
