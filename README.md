# PDF Learning OS

A local-first personal e-learning system for deep technical study from PDF books.

The goal is not to summarize many books quickly. The goal is to convert a personal PDF library into a structured learning path that helps the learner:

`Read → Understand → Recall → Apply → Build / Teach`

## V0.1 Goal

Given 3–5 technical PDF books around one learning goal, the system should:

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
