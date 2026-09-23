# PDF Learning OS

A local-first personal e-learning system for deep technical study from PDF books.

The goal is not to summarize many books quickly. The goal is to convert a personal PDF library into a structured learning path that helps the learner:

`Read → Understand → Recall → Apply → Build / Teach`

## V0.1 Goal

Given a local library of up to roughly 30–100 technical PDF books, the system first maps recorded profiles and helps the learner triage a confirmed 3–5-book study set around one learning goal. For that confirmed set, the system should:

1. Import and catalog PDFs.
2. Extract metadata and table of contents.
3. Build structured book profiles.
4. Compare difficulty, prerequisites, topic coverage, and overlap.
5. Classify each book as CORE / SELECTED CHAPTERS / REFERENCE / SKIP FOR NOW.
6. Recommend a dependency-aware study order.
7. Generate a Markdown study plan.
8. Open one chapter for focused study.
9. Support translation and explanation.
10. Use active recall and quizzes.
11. Record evidence-based mastery.
12. Export durable Markdown learning artifacts.

## Stack

- Frontend: React + TypeScript + Vite + CSS
- Backend: Python + FastAPI
- Persistence: SQLite
- PDF Processing: PyMuPDF
- Tests: Vitest + React Testing Library + Pytest

## Non-goals

No LMS, multi-user accounts, vector DB, RAG, autonomous agents, mobile app, cloud SaaS, arbitrary code execution, or advanced spaced repetition in V0.1.

## Local development (M1)

M0 provides local health checks. M1 adds PDF import, a local book catalog, metadata details, and confirmed deletion. PDF text extraction and learning features remain future milestones.

Tested toolchain: Node 22.20.0, npm 10.9.3, and Python 3.14.5. Supported runtime ranges are Node 22 (at least 22.12) and Python 3.14. Dependency locks are in `frontend/package-lock.json` and `backend/requirements.lock`. npm 10.9.3 successfully installs the frontend lock with `npm ci`. If regenerating that lock, use `npm exec --yes --package npm@11.16.0 -- npm install` to avoid an npm 10 peer-resolution crash; this does not replace your global npm.

### Backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The default database is `data/learning_os.sqlite3` under the repository root, independent of the server's working directory. Its directory is created as needed. To override it, set `PDF_LEARNING_DATA_DIR` in the shell before starting the server. Relative paths resolve against the repository root; `~` is expanded. `backend/.env.example` documents the variable; the backend does not automatically read `.env` files.

M1 requires the explicit Alembic command above. Set `PDF_LEARNING_DATA_DIR` **before both migration and server startup**, using the same value. The migration adds only `books` and `alembic_version`, preserving an existing M0 database. There are no automatic migrations or `create_all()` calls. If the schema is missing/outdated, the library reports setup required. Stop the backend, run `python -m alembic upgrade head`, then restart.

Health still verifies connectivity using `SELECT 1`; it does not guarantee schema or library readiness. If storage initialization fails, fix the directory and restart the backend. Run one backend process per data directory, without multiple workers. A lifetime OS file lock also prevents migrations while the app is running. M1 supports macOS/Linux (`fcntl.flock`); Windows is not supported. Stop one process before starting its replacement, including reload workflows.

### Frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Port 5173 must be available. The default API URL is `http://127.0.0.1:8000`. For an override, copy `frontend/.env.example` to `frontend/.env.local`, change `VITE_API_BASE_URL`, and restart Vite. Frontend environment values are public configuration, never secrets.

The backend allows browser requests from exactly `http://localhost:5173` and `http://127.0.0.1:5173`, without credentials. Both servers bind to loopback.

### Verification

From `frontend/`:

```bash
npm run lint
npm run test -- --run
npm run typecheck
npm run build
```

From `backend/`, with its virtual environment active:

```bash
pytest
```

Tests use temporary migrated SQLite databases, PDF storage, upload spools, and generated PDF fixtures; they do not use the runtime library directory.

With both servers running:

```bash
curl -i http://127.0.0.1:8000/health
```

Expect HTTP 200 and `{"status":"ok","database":"ok"}`. Database failure returns HTTP 503 and `{"status":"error","database":"unavailable"}` without local paths or exception details.

The screen starts with “Checking local connection…” and then shows “Ready”. Stop the backend and reload: it should show “Unavailable”, with stalled requests timing out after five seconds. Restart the backend and reload to confirm recovery. Status is checked on mount, without polling. Confirm the database remains at the configured local path after restart.

Runtime databases, virtual environments, frontend dependencies/builds, and local environment files are ignored. No external service, API key, or PDF is needed to run M0 after dependency installation.


### Using the local PDF library

Choose one PDF (up to **100 MiB**) and click **Import PDF**. Optional title/author override embedded PDF metadata; otherwise the title falls back to the filename. Edition and publication year are stored only when supplied. PDF creation dates are not publication years. No metadata is written back into the PDF.

Imports preserve original bytes. Files must be structurally readable, unencrypted, nonempty PDFs; repaired or malformed PDFs are rejected. Filename extensions and MIME labels alone do not determine validity. Image-only PDFs are allowed, but no text, bookmarks, chapters, or OCR are extracted in M1. The complete multipart request is limited to 101 MiB.

Identical bytes are rejected even under a new filename; **Open existing book** takes you to the existing entry. Different PDFs sharing a filename remain separate books. Select a book title to view its metadata. **Remove book** opens a confirmation; **Cancel** leaves it unchanged. Deletion removes its local PDF and record. Missing originals are reported in the list/details and do not prevent deleting the record. M1 does not include a PDF viewer or metadata editing after import.

Read requests time out after 10 seconds; imports/deletions after 120 seconds. A mutation timeout or network failure means the result may be unknown. The UI refreshes the list; review it before an explicit retry. Requests are never automatically replayed.

### Storage and recovery

Under `PDF_LEARNING_DATA_DIR` (default repository `data/`):

```text
learning_os.sqlite3
.library.lock
books/<uuid>/original.pdf
.staging/<uuid>/original.pdf
.trash/<uuid>/original.pdf
```

Original names are display metadata; storage paths use server-generated UUIDs. Temporary multipart spools use the operating system temporary directory and are closed after completion/error/disconnect.

Imports stage the original before committing its catalog record. Deletes move the original into trash before removing the record. Startup recovery removes abandoned staged imports and uncommitted final files, restores trash whose record still exists, and finishes cleanup for committed deletions. Recovery requires a readable current database and the exclusive data-directory lock.

If file cleanup fails, the UI reports it; retry deletion for a cleanup-pending book. Other mutations cannot proceed until recovery succeeds. For a storage error, stop the backend, check available disk space and permissions, and restart. Unknown files, symlinks, or conflicting book/trash directories stop recovery rather than being overwritten or deleted. Preserve those files for inspection; do not blindly remove a database or storage directory to fix an error.

Back up the **whole data directory with the backend stopped**. Restore database and PDF files together. Do not run a schema downgrade against a populated library: dropping the catalog would make originals unreferenced by startup recovery.

### M1 verification in MODE: TEST

Use a newly created temporary directory as `PDF_LEARNING_DATA_DIR` for both migration and server commands. Start the frontend normally. Import two different PDFs, verify metadata/details, retry identical bytes under a different filename, restart the backend and verify persistence, cancel a deletion, then confirm deletion. Check keyboard navigation and error recovery. Do not point this verification at the learner's real library.

The CODE test suite covers these operations through the API and React component tests. A real-browser lifecycle check remains part of formal MODE: TEST certification.


### Processing a PDF (M2)

Open an imported book and choose **Process PDF**. The backend verifies that the local original still matches the imported SHA-256, then extracts exact per-page text and PDF bookmarks with PyMuPDF. Processing is local and synchronous; the UI shows and persists Not processed, Processing, Processed, or Processing failed.

Extracted page text is PyMuPDF's unsorted text output encoded directly as UTF-8. It is not trimmed, reordered, summarized, normalized, or sent to an external service. References use 1-based physical PDF pages. M2 stores no page text in SQLite and exposes no text/reader endpoint.

A document must contain at least 50 Unicode letters/digits in total and at least one page with 20. Documents below that boundary report that OCR is required. OCR is not supported in V0.1. A failed reprocess keeps the last successful extraction available.

When valid bookmarks exist, the chapter outline preserves their source order and nested levels and shows inclusive page ranges. Invalid bookmark entries are skipped deterministically. With no usable bookmarks, the app creates one clearly labeled **Full document** fallback. Use **Correct fallback sections** to replace fallback/manual structure with flat titled sections and increasing start pages. PDF bookmark structure is read-only, and M2 does not include a chapter reader.

Processing adds these owned paths under the configured data directory:

```text
.processing/<book-uuid>/<attempt-uuid>/pages/000001.txt
books/<book-uuid>/extracted/<generation-uuid>/pages/000001.txt
```

Do not edit these paths. Staged generations are switched atomically through the SQLite active-generation record. Startup finishes safe cleanup, marks interrupted processing failed, and refuses unknown files or symlinks. Deleting a book removes its original, extracted text, page records, and chapter records together.

After updating from M1, stop the backend and run `python -m alembic upgrade head` with the same `PDF_LEARNING_DATA_DIR` used by the server. Existing M1 books become Not processed without changing their metadata or original PDFs.

For M2 verification, use a temporary data directory and disposable PDFs: one multi-page text PDF with nested bookmarks, one text PDF without bookmarks for manual correction, and one image-only PDF for the OCR-required state. Verify reprocessing, backend restart persistence, and final deletion before using learner data.

### Learning goals (M3)

After importing at least three books, use **Learning goal** to create one active goal with a title, optional description, and 3–5 selected books. Processing is not required for selection. Starting another goal keeps the prior goal as inactive history and makes the new goal the only active one.

Use **Change selected books** to replace the active goal's complete selection while keeping 3–5 books. A selected book cannot be deleted from the library until it is replaced in the active goal; the API returns a clear conflict without changing the book or its files.

M3 adds `POST /learning-goals`, `GET /learning-goals/active`, and `PUT /learning-goals/{goal_id}/books`. After updating from M2, stop the backend and run `python -m alembic upgrade head` with the same `PDF_LEARNING_DATA_DIR`; revision `0003_learning_goals` preserves all existing library and extraction data.

### Book profiles (M4)

Open a book's details and use **Book profile** to record its domain, difficulty, prerequisites, main topics, theory/practice orientation, strengths, weaknesses, and suggested use. Only one current profile is kept per book. Editing replaces the complete profile while preserving its creation time; blank scalar values and empty lists mean that a field has not been recorded.

List fields accept one item per line and reject case-insensitive duplicates and configured item/count limits. At least one profile field is required. Every populated M4 field is labeled as manually entered. Client requests cannot supply provenance, and M4 performs no AI inference, PDF text reading, comparison, role classification, or goal-specific analysis. Any catalog book can be profiled regardless of processing state or whether its original PDF is currently available.

M4 adds `GET /books/{book_id}/profile` and `PUT /books/{book_id}/profile`. After updating from M3, stop the backend and run `python -m alembic upgrade head` with the same `PDF_LEARNING_DATA_DIR`; revision `0004_book_profiles` preserves existing books, extracted content, learning goals, and associations. Deleting a book also removes its profile through the existing database cascade.

### Book comparison (M5)

In the active learning goal, choose **Compare selected books**. Each selected book needs a profile with at least one main topic; readiness messages link to its existing profile panel. Processing is not required. Unrecorded optional facts remain unknown.

The overview and expandable sections compare recorded topics, difficulty, prerequisites, and overlap. Matching only collapses whitespace and ignores case: `ML` does not match `machine learning`. Topic counts describe recorded coverage, not teaching quality or completeness. Empty prerequisites mean “not recorded.”

Choose **Classify books** and assign every book one role with a written rationale:

- CORE: primary resource, not necessarily every chapter.
- SELECTED CHAPTERS: selected parts covering one or more chosen profile topics; exact chapters come later.
- REFERENCE: consult as needed.
- SKIP FOR NOW: defer for this goal.

Explain each book’s relevance, including when unknown. Optionally assess depth and practice with explanations; neither is inferred from difficulty or theory/practice orientation. Optional evidence checkboxes reference profile facts, recorded topics, or pairwise results, not extracted PDF evidence. Confirm review for each book before saving. Multiple or no CORE books are allowed.

One saved comparison is retained per goal. Editing replaces it atomically. Profile or goal-selection changes mark it stale without erasing the old result. **Review with current inputs** carries existing judgments forward for explicit review and flags obsolete references. Refresh also runs on window focus; concurrent edits are rejected rather than overwritten. A failed or ambiguous save preserves the draft and reloads authoritative state without replaying the request. Deleting a book removes saved comparisons containing it; active-goal book deletion remains protected.

API: `GET /learning-goals/{goal_id}/comparison` returns readiness, `input_token`, current preview, saved snapshot, and stale reasons. `PUT` accepts the returned token, `expected_revision` (null for first save), and the complete selected book assessments, each with `reviewed: true`. It returns the same envelope. Missing goals return 404; inactive/unready goals, changed inputs, or revision conflicts return 409; invalid fields/references return 422. Field shapes and persistence rules are documented in `ARCHITECTURE.md` and the backend OpenAPI schema.

After updating from M4, stop the backend and run `python -m alembic upgrade head` before restarting. The new head `0005_book_comparisons` preserves all M1–M4 rows and artifacts. For disposable verification, set `PDF_LEARNING_DATA_DIR` to a fresh temporary directory before migrating or starting the backend. M5 adds no AI, provider keys, semantic matching, new dependencies, learning path, chapter sequencing, or study plan.

### Library intelligence and curriculum triage (M5.5)

Open **Library intelligence** below the book list to work with a 30–100-book candidate library. The compact map is searchable and filterable by readiness, domain, topic, difficulty, orientation, processing state, and current candidate membership. Processing and TOC state are informational: triage uses only catalog metadata and manually recorded M4 profiles. The profile-readiness queue opens the existing profile editor and advances to another incomplete book after a save.

Duplicate, edition, recorded-topic, and prerequisite sections use exact normalized metadata/profile matching. Whitespace is collapsed and case is ignored; punctuation, aliases, synonyms, acronyms, translations, and embedded edition suffixes are not guessed. Exact PDF bytes remain governed by import-time duplicate rejection, and hashes are never exposed. A probable-duplicate review records same work, related edition, or distinct; it never deletes or merges a book. Relationship and prerequisite lists are paginated.

Create a curriculum triage with a title, 1–25 target topics, optional description/domain/difficulty ceiling, and either a snapshot of the current library or an explicit candidate subset. Only one draft is editable. Starting a replacement explicitly archives that draft when the replacement is successfully created. Whole-library imports/deletions and relevant profile/review changes produce a visible stale state; use **Save and synchronize triage** before confirmation. Applied/archived/invalidated sessions remain read-only history.

The deterministic shortlist labels its exact evidence and never supplies a numeric score or study order. It can return fewer than three books when the recorded evidence is insufficient. You may manually choose another 3–5 ready candidates, including books above the optional ceiling. For every selected book, provide an M5-compatible role, rationale, relevance explanation, optional depth/practice assessment, optional evidence, focus topics for SELECTED, and explicit review confirmation. At least one book must be CORE or SELECTED; LATER is not part of Books Now.

Final confirmation is atomic: it deactivates the old active goal, creates the confirmed M3 goal, creates revision 1 of its reviewed M5 comparison, and marks the triage applied. A conflict leaves all four states unchanged. Active-goal deletion protection remains in force; later deletion of an inactive book removes affected comparison data and invalidates only affected applied triage history.

M5.5 adds `GET /library-intelligence/map`, paginated relationship/prerequisite reads, relation-review `PUT`, and `/curriculum-triages` lifecycle endpoints. After updating from M5, stop the backend and run `python -m alembic upgrade head`; head `0006_library_intelligence` preserves M1–M5 data and files. M5.5 adds no AI, full-PDF analysis, fuzzy/semantic matching, graph, learning-path order, chapters, schedule, or study-plan artifact.
