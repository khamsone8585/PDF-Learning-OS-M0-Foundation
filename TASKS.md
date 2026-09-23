# TASKS.md — PDF Learning OS

Status: TODO / PLANNED / IN PROGRESS / BLOCKED / READY FOR TEST / DONE

## M0 — Repository Foundation
**Status:** DONE

Create React+TS+Vite frontend, FastAPI backend, SQLite, frontend tests, backend tests, and `GET /health` integration. No AI or PDF feature yet.

## M1 — Local PDF Library
**Status:** DONE

Import, save, list, open details, and delete local PDFs.

## M2 — PDF Processing
**Status:** DONE

Extract metadata, page text, TOC, chapter/page mapping, and clear errors using PyMuPDF. No OCR.

## M3 — Learning Goals
**Status:** DONE

Create one active learning goal and associate 3–5 books.

## M4 — Book Profiles
**Status:** DONE

Difficulty, prerequisites, topics, strengths, weaknesses, theory/practice orientation, and editable profile.

## M5 — Book Comparison
**Status:** DONE

Compare overlap, prerequisites, difficulty, coverage, classify book role, and explain rationale.

## M5.5 — Library Intelligence & Curriculum Triage
**Status:** DONE

Map and triage a 30–100-book candidate library, review deterministic duplicate/prerequisite/overlap evidence, and confirm 3–5 books into the existing M3/M5 contracts.

## M6 — Learning Path
**Status:** TODO

Generate dependency-aware stages, selected chapters, skip/reference decisions, and ordering rationale.

## M6.5 — 90-Day Study Planner
**Status:** TODO

Turn an approved dependency path into a dated 90-day study plan. Markdown rendering remains M11.

## M7 — Chapter Study Reader
**Status:** TODO

Chapter navigation, source text, page context, selected-text interaction, readable layout.

## M8 — Translation & Explanation
**Status:** TODO

Thai, Lao, simplified English, simple/academic/technical explanations, preserve technical terms, label generated content.

## M9 — Active Recall & Quiz
**Status:** TODO

Explain-back, feedback, recall questions, quiz, reveal rationale, preserve source scope.

## M10 — Mastery & Progress
**Status:** TODO

Mastery 0–5, evidence records, progress, review-needed state, manual correction.

## M11 — Markdown Artifacts
**Status:** TODO

Export PROFILE.md, STUDY_PLAN.md, CHAPTER_NOTES.md, PROGRESS.md, optional TEACHING_NOTE.md.

## M12 — Pilot Validation
**Status:** TODO

Use 3 real technical PDFs and one learning goal for 2–4 weeks. Evaluate extraction, learning-path quality, explanations, recall, mastery, and friction. Only after this consider RAG/embeddings.

## Historical M0 task

Task: M0 — Repository Foundation
Milestone: M0
Mode: TEST
Status: DONE
Approval: User approved implementation of the final M0 plan and acceptance criteria on 2026-09-17.

Goal:
Establish the smallest runnable local development foundation for PDF Learning OS: React + TypeScript + Vite frontend, FastAPI backend, SQLite connectivity, frontend/backend tests, and a verified `GET /health` integration. Do not implement PDF, AI, learning, or domain behavior.

Current-state findings (PLAN baseline; see implementation record below):
- Source-of-truth documents reviewed: `AGENTS.md`, `PROJECT.md`, `SOFTWARE_REQUIREMENTS.md`, `ARCHITECTURE.md`, `LEARNING_MODEL.md`, `TASKS.md`, and `CHANGELOG.md`.
- `CHANGELOG.md` reports no verified implementation changes yet.
- M0 is the first milestone and is already PLANNED; this session refines the existing plan.
- The required stack is React + TypeScript + Vite + CSS, FastAPI, SQLite, Vitest + React Testing Library, and Pytest.
- `ARCHITECTURE.md` defines the long-term frontend/backend direction, but M0 must not pre-create future domain services or tables merely because they appear in the architecture sketch.
- `GET /health` is already part of the API sketch.
- SQLite is the persistence target, but no ORM/data-access library is specified by the source-of-truth documents.
- npm is implied by the required frontend quality-gate commands in `AGENTS.md`.
- No exact Python version, Node version, Python dependency manager, database access library, local data-directory convention, or health-response contract is specified.
- Workspace inspected on 2026-09-17: project Markdown documents and `.kilo` metadata only; no frontend/backend source, dependency manifests, or tests exist.
- No `.git` directory exists. `git status --short` failed with “not a git repository”; Git diff is unavailable. Do not describe the workspace as a clean Git checkout.
- The IDE-mentioned `TASKS_M0_PLAN.md` is absent on disk. Keep this plan in `TASKS.md` rather than creating a second status/plan source.
- Observed toolchain: Node v22.20.0, npm 10.9.3, Python 3.14.5. These are installed versions, not verified dependency compatibility.
- Before MODE: CODE, recheck the workspace and confirm approval of this task and its acceptance criteria.

Files expected to change:
- `.gitignore`
- `README.md` (development/setup section only)
- `ARCHITECTURE.md` (selected M0 configuration/dependency decisions only)
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/index.html`
- `frontend/.env.example`
- `frontend/src/vite-env.d.ts`
- `frontend/tsconfig*.json`
- `frontend/vite.config.ts`
- `frontend/eslint.config.*` or the Vite-generated equivalent
- `frontend/src/main.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/api/health.ts`
- `frontend/src/styles/index.css`
- `frontend/src/test/setup.ts`
- `frontend/src/app/App.test.tsx`
- `backend/pyproject.toml`
- `backend/requirements.lock` (resolved, pinned runtime and test dependencies)
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/api/__init__.py`
- `backend/app/api/health.py`
- `backend/app/db/__init__.py`
- `backend/app/db/connection.py`
- `backend/tests/conftest.py`
- `backend/tests/test_health.py`
- `backend/tests/test_db.py`
- `TASKS.md`

Implementation plan:
1. At the start of MODE: CODE, confirm task approval and acceptance criteria, then recheck workspace files, runtime versions, and Git availability. Preserve existing documentation and `.kilo` metadata. Git initialization, commits, and remote configuration are separate from this scaffold task.
2. Use npm with a recorded `package-lock.json` for the frontend. Use Python `venv` + pip, declare backend dependencies in `pyproject.toml`, and record a reproducible pinned dependency set in `requirements.lock`. Validate package compatibility with the observed runtimes before scaffolding; document a supported alternative if Python 3.14 is incompatible, without changing the global interpreter. Choose exact package versions during CODE and record the supported/tested runtimes in README.
3. Scaffold only the minimum React + TypeScript + Vite application needed to render the app shell and backend health state. Do not create empty future feature folders solely to mirror the long-term architecture.
4. Configure Vitest + React Testing Library and one shared test setup file.
5. Create a small frontend health API client and have the app shell display deterministic loading, ready, and unavailable states.
6. Create the FastAPI application with a thin health route.
7. Approved database decision: use SQLAlchemy 2.x against SQLite. Do not create M1 domain models/tables in M0.
8. Configure the local data directory through `PDF_LEARNING_DATA_DIR`, defaulting to repository-root `data/` resolved from the application location rather than the current working directory. Expand `~`, resolve relative overrides against the repository root, create missing directories, and use `learning_os.sqlite3` inside that directory. Ignore runtime data, SQLite sidecar files, `.env`, virtual environments, caches, and build output; keep `.env.example` trackable. Dispose database resources cleanly and use temporary paths in tests.
9. Do not add Alembic yet because M0 creates no persistent domain schema. Introduce migrations with the first real schema change unless the actual repository already contains a migration convention.
10. Define `GET /health` as HTTP 200 with exactly `{"status":"ok","database":"ok"}` after SQLite `SELECT 1` succeeds. Database initialization/connectivity/query failure returns HTTP 503 with exactly `{"status":"error","database":"unavailable"}`. Handle database initialization errors so this endpoint remains available to report failure; omit paths, SQL, and exception details from responses. This checks connectivity only, not migrations, write readiness, or future domain behavior.
11. Bind development servers to loopback. Use `VITE_API_BASE_URL` with default `http://127.0.0.1:8000`; configure FastAPI CORS for exactly `http://localhost:5173` and `http://127.0.0.1:5173`, without credentials or wildcard origins. Set Vite to port 5173 with strict port selection. Include environment examples and explain how to set backend variables in the shell; do not imply automatic `.env` loading unless implemented.
12. Add backend tests for SQLite connectivity and the exact health contract.
13. Make one bounded health request on mount with a five-second timeout and cleanup cancellation. Show loading, ready only for the exact successful contract, and unavailable for HTTP errors, network errors, malformed/unexpected payloads, or timeout. Expose status updates accessibly (for example, a status live region). No polling or retry UI is required. Test these states with mocked fetch and controlled timers; allow React development StrictMode effect cleanup without stale updates. Do not add Playwright/E2E infrastructure in M0.
14. Add README commands with explicit working directories for installing locked dependencies, creating/activating the backend virtual environment, running both servers, configuring local paths/origins, and executing all quality gates. Include `curl` health verification and describe the expected startup/failure UI. Record the selected M0 configuration and dependency decisions in `ARCHITECTURE.md` during CODE, keeping workflow/status in `TASKS.md`.
15. Update `TASKS.md` to `READY FOR TEST` only after CODE is complete. Do not mark DONE and do not update `CHANGELOG.md` until MODE: TEST passes.

Data / Schema Impact:
- Establish SQLite connectivity and runtime database-file location only.
- No `books`, `chapters`, learning-goal, mastery, or other domain tables in M0.
- No migration is required while no persistent domain schema exists.
- The database abstraction chosen in M0 must allow future schema/migration work without changing API behavior.

Acceptance criteria:
- Frontend starts locally using the repository's npm workflow.
- Backend starts locally with FastAPI.
- SQLite connectivity succeeds using the configured local data path; a file is created at the documented location, and reopening it after application restart succeeds without deletion/recreation logic. No domain tables are created.
- `GET /health` returns the exact HTTP 200 success contract above when SQLite is reachable and the exact HTTP 503 failure contract above when initialization or connectivity fails, without leaking local paths or exception details.
- The frontend calls the real backend health endpoint in local development and visibly/accessibly distinguishes loading, ready, and unavailable states; unreachable or stalled requests become unavailable within five seconds.
- Documented localhost origins receive the expected CORS headers; an unrelated origin does not receive an allow-origin header.
- README setup works with the selected supported runtimes and locked dependencies; no AI keys, external services, or PDF files are needed.
- Frontend has Vitest + React Testing Library tests covering its M0 behavior.
- Backend has Pytest tests covering SQLite connectivity and the health endpoint.
- `npm run lint` passes.
- `npm run test -- --run` passes.
- `npm run build` passes.
- `npm run typecheck` passes if configured.
- `pytest` passes.
- No PDF processing, PyMuPDF workflow, AI provider, authentication, domain tables, RAG, embeddings, or later-milestone behavior is introduced.
- `TASKS.md` is updated to `READY FOR TEST` after coding, not DONE.

Test plan:
- Backend unit/integration: initialize/connect to a temporary SQLite database, execute a lightweight query, dispose/reopen the connection, and verify the same file remains. Check default path resolution independently of the working directory, relative/absolute overrides, and missing directory creation. Test overrides must prevent all writes to repository runtime data.
- Backend API: call `GET /health` with FastAPI's test client and assert status code and exact JSON contract.
- Backend failure paths: inject initialization and query/connectivity failures and assert the exact 503 JSON with no exception or path leakage; avoid platform-dependent chmod-only tests.
- Backend CORS: assert headers for both allowed origins and absence of allow-origin for an unrelated origin.
- Frontend: render the app and assert the health loading state.
- Frontend: mock a successful health response and assert the ready state.
- Frontend: cover HTTP 503, rejected fetch, malformed JSON, unexpected payload, and five-second timeout; assert unavailable and verify unmount cleanup avoids stale state updates.
- Quality gates: `npm run lint`, `npm run test -- --run`, `npm run build`, optional `npm run typecheck`, and backend `pytest`.
- Manual local integration check in TEST mode: follow README from a fresh dependency install, run both servers, verify `/health` via curl and the browser ready state, stop the backend and reload to verify unavailable, restart and reload to verify recovery, and confirm SQLite remains at the documented local path.
- Run frontend commands from `frontend/` and `pytest` from `backend/` with its virtual environment active. Record actual results in TASKS.md during TEST; only after all acceptance criteria and required checks pass mark DONE and update CHANGELOG.md.

Risks / edge cases:
- Files can change between PLAN and CODE; recheck before scaffolding and preserve existing user changes. Git-based diff/recovery is unavailable until a repository is initialized separately.
- Installed Python 3.14.5 may limit compatible dependencies. Verify resolution during CODE and record any needed runtime adjustment; dependency installation and compatibility have not been tested in PLAN.
- SQLite paths can accidentally be committed; runtime data must be ignored.
- Running tests must use temporary database paths so tests do not modify the learner's real local database.
- Permissive CORS would weaken the local-first boundary; allow only the required local development origins.
- A health endpoint that always returns OK would not verify SQLite foundation; include a lightweight database ping.
- Creating all future architecture folders/tables now would overengineer M0 and blur milestone boundaries.

Out of scope:
- PDF import or PyMuPDF processing
- book/chapter/domain schemas
- OCR
- learning goals
- book analysis/comparison
- learning-path logic
- AI provider implementation
- translation/explanation
- recall/quiz
- mastery/progress
- Markdown export
- authentication
- RAG, embeddings, vector databases, agents
- cloud deployment, Docker, CI/CD, mobile, realtime collaboration
- browser E2E framework
- Git initialization, commits, remotes, and publishing

Test results:
CODE verification on 2026-09-17:
- Frontend clean locked install: `npm ci --offline --cache /tmp/pdf-learning-os-npm-cache` passed on npm 10.9.3.
- `npm run lint`: passed.
- `npm run test -- --run`: passed, 11 tests on Vitest 4.1.11.
- `npm run typecheck`: passed.
- `npm run build`: passed on Vite 7.3.6.
- Backend `.venv/bin/pytest`: passed, 13 tests on Python 3.14.5.
- Backend `pip check`: passed.
- Frontend patched dependency installation audit: zero vulnerabilities.
- Live Uvicorn smoke: HTTP 200 with exact health JSON using `/tmp/pdf-learning-os-m0-smoke`, isolated from runtime learner data.
- Live Vite smoke: HTTP 200 serving the application entry point.
- Browser ready/unavailable/recovery check: pending MODE: TEST; computer-use tooling reported no available browser. Mocked frontend state/failure tests passed, but do not replace the real browser check.
- Two upstream backend deprecation warnings (Starlette HTTPX integration and AnyIO portal alias); no test failures. npm also reports upstream ESLint/whatwg-encoding deprecation notices.
- No Git repository exists; status/diff remain unavailable. No Git initialization performed.

Implementation record:
- Implemented the approved M0 shell, exact health contracts, local SQLite path configuration, engine lifecycle cleanup, restricted CORS, five-second frontend timeout, and isolated tests.
- Added dependency locks, environment examples, ignore rules, README setup/verification instructions, and M0 architecture decisions.
- npm 10 dependency resolution crashed while upgrading Vitest; generated the lockfile with a temporary npm 11.16.0 invocation. A subsequent clean npm 10.9.3 install and all frontend gates passed. Global toolchain was unchanged.
- No domain tables, PDF/AI/learning features, or future service stubs added.
- Smoke servers stopped after verification. Temporary smoke database remains outside the repository.
- CODE complete; status is READY FOR TEST, not DONE. CHANGELOG.md unchanged. Formal TEST review and real browser verification remain.

Notes:
- Minor documentation-process inconsistency: `NEW_CHAT_PROMPT.md` lists `CHANGELOG.md` as mandatory reading before every task, while the `AGENTS.md` required-reading list does not explicitly include it. This does not affect M0 behavior; `AGENTS.md` remains authoritative for workflow rules.
- `README.md` is a shorter product summary and omits some extraction details present in the requirements; this is treated as summarization, not a product contradiction.
- User approval covers the M0-specific choices above, including SQLAlchemy 2.x for SQLite access, no Alembic until the first real schema, and the health-response contract.


## M0 final TEST certification — 2026-09-17

Result: PASS. Milestone M0 / Mode TEST / Status DONE. Earlier CODE results and pending-browser notes above are historical; this certification supersedes them.

Required quality gate (final run, no defects or code changes):

| Working directory | Exact command | Result |
| --- | --- | --- |
| frontend | `npm run lint` | PASS, exit 0 |
| frontend | `npm run test -- --run` | PASS, 1 test file, 11 tests passed, 0 failed |
| frontend | `npm run build` | PASS, exit 0, Vite 7.3.6 |
| frontend | `npm run typecheck` | PASS, exit 0 |
| backend | `source .venv/bin/activate && pytest` | PASS, 13 tests passed, 0 failed, 2 upstream deprecation warnings |

Acceptance evidence:
- Documented FastAPI startup verified with `source .venv/bin/activate && PDF_LEARNING_DATA_DIR=/tmp/pdf-learning-os-m0-test-20260917 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from backend. The documented data-directory override isolated integration data from the learner library.
- Documented frontend startup `npm run dev` from frontend served HTTP 200 at `http://127.0.0.1:5173/`.
- A Python standard-library `urllib.request` HTTP probe asserted the exact 200 JSON `{"status":"ok","database":"ok"}` for all three tested origins. Both approved origins received their matching allow-origin header; `https://unrelated.example` received none. The probe also asserted HTTP 200 for the Vite entry and confirmed port 8000 in the served health client.
- Backend tests verified actual SQLite connectivity, file creation/reopening without domain tables, relative/absolute/default paths, safe 503 initialization/query/connection failure contracts, and CORS preflight behavior.
- Inspected all database fixtures: autouse temporary directory override and explicit `tmp_path` storage; default-path checks only resolve paths and do not create a learner database. Repository `data/` remained absent before/after the integration run.
- The integration SQLite file existed under the explicit /tmp test directory, contained zero tables, and retained the same inode (21573799) after backend restart.
- Inspected `.gitignore`: `/data/`, SQLite files and sidecars, environment files, dependencies, caches, and build outputs are excluded; environment examples remain trackable. Git ignore configuration is present, but Git-based verification is unavailable without a repository.
- Frontend automated tests verified loading, ready, HTTP/network errors, malformed/unexpected payloads, five-second timeout, cleanup, and StrictMode stale-request handling.
- Real-browser manual verification PASSED in Safari using native computer-use tooling: Ready with backend running; Unavailable after stopping backend and reloading; Ready after restarting backend and reloading. Rendered screenshot inspected. The browser connector itself had no attached browser; native Safari provided the required verification. Chrome was not used because user activity interrupted its automation.
- Ports and API configuration agree: frontend 127.0.0.1:5173, backend 127.0.0.1:8000, and localhost/127.0.0.1 port 5173 CORS origins only.
- Source/configuration inventory contains only M0: no domain tables, PDF processing, AI, learning features, future services, or M1+ behavior. Source integrity preserved.
- All explicit M0 acceptance criteria passed. No remaining acceptance blocker.

Defects fixed: none. No production code, dependency, or test changes during TEST.
Files changed during TEST: TASKS.md and CHANGELOG.md only (excluding generated test/build caches).
Git commands attempted: `git status --short` (exit 128) and `git diff --stat` (exit 129), both unavailable because this workspace is not a Git repository. Git was not initialized.
Limitations: two non-failing upstream warnings for Starlette HTTPX integration and the AnyIO portal alias. Git diff/status cannot be supplied. No browser framework added.
Cleanup: both integration servers stopped. Isolated /tmp smoke database retained; no learner data modified.
M1 remains TODO. Stop after M0 TEST.

## Git baseline before M1 — approved follow-up

Milestone: Repository maintenance (between M0 and M1)
Mode: CODE
Status: DONE
Approval: User approved the Git Baseline Before M1 plan and its local commit on 2026-09-17.

Goal: establish one local baseline commit of exactly the approved 38 project files on main.
Scope: add the approved ignore patterns, initialize Git at the project root, stage the explicit manifest, inspect the staged diff, commit, and verify branch/file inventory/clean working tree/no remotes.
Acceptance: main branch; exactly 38 approved tracked files; local artifacts ignored and environment examples tracked; one reviewed baseline commit; clean working tree; no remote.
Files edited: .gitignore and TASKS.md only. Existing M0 source, tests, dependencies, documentation, and certification otherwise preserved.
Commit message: `chore: establish verified M0 baseline`.
No application recertification required by this approved maintenance plan. M0 stays DONE; M1 stays TODO. No remote, push, global identity change, dependency change, or application refactor.

Pre-commit verification: Git initialized on main; 23 ignore probes passed; all 38 approved files (including both .env.example files) remain trackable; unignored inventory exactly matches the manifest. Credential-pattern scan found no matches. Only .gitignore and TASKS.md were edited; no runtime files removed.
Final commit/tree/status verification is performed after creating the baseline and reported in the task response. This CODE record does not change M0 certification or mark a new product milestone DONE.


Repository-maintenance verification: baseline `6c4c168` was committed and pushed to origin/main at https://github.com/khamsone8585/PDF-Learning-OS-M0-Foundation.git. Main tracks origin/main; clean tree verified before M1. Earlier no-remote statements describe the original local-only scope.

## Historical M1 task

Task: M1 — Local PDF Library
Milestone: M1
Mode: TEST
Status: DONE
Approval: User explicitly approved the complete M1 plan and implementation on 2026-09-18.

Goal: FR-001–005 only: import, preserve locally, list, inspect bibliographic details, and confirm deletion.

Approved decisions: books UUID schema with title, normalized original filename, nullable author/edition/year, positive page count, UTC import time, unique SHA-256 and bounded byte size. Paths derive from UUID. Optional import metadata overrides PDF title/author; no publication-date inference. Explicit Alembic initial migration, never create_all/startup migrations. Add only Alembic, PyMuPDF and python-multipart. 100 MiB PDF / 101 MiB request limits. Reject invalid, empty, repaired and encrypted PDFs; inspect pages without text/TOC/rendering. Reject duplicate bytes with existing ID; allow different bytes sharing a name.

Storage: books/<uuid>/original.pdf, .staging/<uuid>, .trash/<uuid> under configured data directory. Single-process flock plus serialized operations; no user-controlled paths, symlinks or overwrite. Stage/hash/inspect, insert, move, commit; compensate uncertain outcomes using a fresh DB read. Delete through trash; restore if record remains, clean if committed. Startup reconciliation never operates without readable current schema. Report cleanup failures and block unsafe mutations.

Interfaces: POST /books multipart plus optional title/author/edition/year -> 201; GET /books -> books array; GET /books/{uuid} -> book; DELETE -> 204. Safe structured errors, duplicate 409, validation 422, size 413, media 415, malformed multipart 400, missing 404, storage/setup 503. Responses omit hash/path and include file_available. Existing health contract preserved.

Frontend: accessible file/metadata form, bounded requests, loading/errors/retry, list, details, duplicate navigation, explicit inline delete confirmation, missing-file and unknown-outcome recovery. No optimistic deletion or automatic mutation retry.

Files: backend config/startup/dependencies, models/schemas/library routes/services/storage/PDF inspector, Alembic environment/revision, tests; frontend library API/components/tests and app/styles; ARCHITECTURE.md, README.md, TASKS.md. CHANGELOG.md unchanged in CODE.

Implementation order: dependencies/schema/locking; temporary migration fixtures; inspection/storage/library service; routes/body limits; frontend; recovery tests; documentation and checks.

Acceptance criteria:
1. Valid <=100 MiB PDF creates one record and byte-identical original.
2. Metadata precedence and null unknown edition/year are correct.
3. Records/files survive restart.
4. Identical bytes return 409 without duplicate storage; same-name different bytes succeed.
5. Invalid/empty/repaired/encrypted/oversized/unreadable inputs leave no visible partial books.
6. List/details schema, ordering and not-found contracts pass.
7. Names/IDs cannot escape storage or overwrite files.
8. Confirmed delete removes owned data; cancel does nothing; missing-file delete succeeds.
9. Failure/crash recovery follows committed DB state and reports cleanup failures.
10. Explicit migration supports fresh/M0 DBs; absent schema gives setup error.
11. UI library flows are keyboard accessible.
12. Tests isolate DBs, storage, generated PDFs and upload spools in temporary paths.
13. Existing health and frontend lint/test/typecheck/build plus pytest pass.
14. No M2 behavior or infrastructure.

Test plan: migration idempotence/constraints; metadata/size boundaries; invalid PDFs; duplicates/concurrency; path and symlink safety; restart; import/delete fault injection and recovery; UI loading/errors/confirmation/focus/stale responses/timeouts. Formal TEST additionally runs browser lifecycle against a temporary library.

Risks: SQLite/filesystem require compensation, disk failure can defer cleanup, structural validation cannot guarantee later extraction, strict PDF rejection, single-process serving, unknown network outcomes. Out of scope: M2 extraction/TOC/OCR/AI, viewer/download, editing/search/bulk/pagination, cloud/auth/multiworker.

CODE verification — 2026-09-18:
- Implemented the approved FR-001–005 schema/migration, guarded UUID storage, structural PDF inspection, bounded multipart upload, duplicate policy, import/delete compensation and startup recovery, thin API and accessible library UI.
- Added Alembic 1.20.0, PyMuPDF 1.28.2, python-multipart 0.0.32 and their Mako/MarkupSafe dependencies to the existing Python 3.14.5 virtual environment and lockfile. Existing locked versions preserved; pip check passed. No frontend dependency changes.
- Backend: 64 tests passed (including existing 13 M0 tests). Final command from repository root: `backend/.venv/bin/pytest -q -c backend/pyproject.toml backend/tests`. Standard backend-directory pytest also passed during development.
- Frontend: `npm run test -- --run` passed, 28 tests across 3 files; `npm run lint`, `npm run typecheck`, `npm run build` all passed.
- Failure coverage includes ambiguous commits, failed DB flush/commit, moves/restores/cleanup, blocked mutations and recovery, UUID collision, path/symlink/unknown-entry protection, stale schema, byte limits independent of Content-Length, truncated multipart and disconnect spool closure, encrypted/repaired/unreadable PDF rejection, and UI mutation uncertainty/stale details/focus/confirmation.
- CODE fixes found through verification: compensation reads use a fresh Core connection (no ORM autoflush); unknown storage entry names map to storage errors; incomplete multipart must reach its final boundary; spool IO errors use safe 503 responses; UTC timestamps always include microseconds for lexical chronological sorting.
- `git diff --check` passed. CHANGELOG.md unchanged. No real learner library/database created or migrated; all migration/PDF tests used temporary directories. No commit or push performed.
- Non-failing upstream warnings: existing Starlette HTTPX/AnyIO deprecations plus PyMuPDF SWIG type deprecations.
- Formal MODE: TEST remains required, including real-browser import/details/duplicate/restart/cancel/delete checks with temporary data. Automated checks do not substitute for that browser certification.
- M0 remains DONE, M1 is READY FOR TEST (not DONE), M2 remains TODO.


## M1 formal TEST attempt — 2026-09-18

Result: automated, migration, scope, and live HTTP checks PASS. Overall certification INCOMPLETE: required real-browser verification could not run. M1 remains READY FOR TEST, Mode TEST; M0 remains DONE and M2 remains TODO. CHANGELOG.md is not updated.

Required quality gate:

| Working directory | Exact command | Result |
| --- | --- | --- |
| backend | `source .venv/bin/activate && pytest` | PASS, 64 collected, 64 passed, 0 failed, 7 upstream warnings |
| backend | `source .venv/bin/activate && python -m pip check` | PASS, no broken requirements |
| frontend | `npm run lint` | PASS, exit 0 |
| frontend | `npm run test -- --run` | PASS, 3 files, 28 passed, 0 failed |
| frontend | `npm run typecheck` | PASS, exit 0 |
| frontend | `npm run build` | PASS, exit 0, Vite 7.3.6 |

Migration/live test:
- Disposable root: `/var/folders/gx/n5qy94qd5xg4hv43mrd775mr0000gn/T/pdf-learning-os-m1-test-y6emj36h`; PDF_LEARNING_DATA_DIR was its `library` subdirectory; TMPDIR was its `spools` subdirectory.
- Orchestration command from repository root: `backend/.venv/bin/python /tmp/pdf-learning-os-m1-live-test.py`. The script explicitly passed the project venv interpreter and identical environment to migration and both backend starts.
- From backend, `python -m alembic upgrade head` ran twice against the fresh temporary database: both exit 0. SQLite inspection found only books and alembic_version, revision 0001_books, ten book columns and no BLOB columns. No downgrade criterion added or downgrade performed.
- Backend command: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Frontend command from frontend: `npm run dev`. Both served HTTP 200. Initial sandbox loopback binding failed with PermissionError; the authorized network-enabled execution then passed. This was a sandbox restriction, not an application defect.
- Live POST /books returned 201 with correct embedded title/author, supplied edition/year, and page count. GET /books and GET /books/{id} matched the response. Stored original bytes matched the disposable PDF exactly; SQLite hash/byte count matched the owned file.
- Same bytes under both original and different filenames returned 409 with existing ID. Different PDF bytes sharing a filename created a separate book. Non-PDF and zero-byte input returned 422.
- Allowed loopback CORS origins passed; unrelated origin had no allow-origin header. Unknown book returned 404. An encoded arbitrary-path DELETE was rejected, leaving an unrelated sentinel file unchanged.
- Backend was stopped/restarted against the same temporary database. Metadata, PDF bytes, and stored-file inode persisted.
- DELETE returned 204, removed only the intended owned directory/row, and left the second book and unrelated sentinel intact. A second deletion with its original manually removed also returned 204. Final books query and all owned books/staging/trash directories were empty; SQLite book count was zero.
- Report and server logs retained in the disposable root (`report.json`, backend-first.log, backend-restart.log, frontend.log). Report result PASS. Both server processes were stopped; no listeners remained on ports 8000/5173. Repository data/ remained absent before and after verification.

Real browser:
- Attempted computer-use initialization: `await cua.getState()`.
- Exact failure: `CUA_REPL_ENABLED_SURFACES is required`.
- No alternative callable browser/native-computer tool was exposed. No Playwright or other browser dependency installed.
- Browser import/loading/details/duplicate/confirmation/deletion/reload, visual keyboard checks and console inspection are NOT verified. React component tests cover these behaviors but do not replace the explicit real-browser acceptance gate.
- Required next step: resume the browser verification with working browser/computer-use surfaces against a temporary library. Only after that gate passes may M1 be marked DONE and CHANGELOG.md updated.

Scope/source review:
- Reviewed M1 routes, library/storage/PDF services, database configuration/model/migration, and backend/frontend tests and Git changes. Routes delegate library behavior to the service; original filenames are not storage paths. File validation, hash uniqueness, recovery/rollback, missing-file deletion and path/symlink protections have regression coverage.
- No full text extraction, TOC, chapter mapping, OCR, processing pipeline, AI/RAG/embeddings/vector DB, auth, learning goals or later-domain behavior introduced. PDF binaries remain filesystem originals rather than SQLite BLOBs.
- Test fixtures use temporary databases, storage, generated PDFs and upload spools. Git ignore probes passed for original PDFs, staging/trash and SQLite under data/. Source integrity preserved.

Defects found/fixed: none. No source, migration, dependency, or test changes during this TEST attempt.
Files changed during TEST: TASKS.md only; disposable script, fixtures, databases and logs are outside the repository, and normal test/build artifacts are ignored.
Git: main tracks origin/main at 6c4c168; existing uncommitted M1 implementation remains present. No commit/push. `git diff --check` passed. Total Git diff includes earlier CODE work, not just this TEST record.
Warnings: seven non-failing upstream warnings (Starlette HTTPX integration, AnyIO alias and PyMuPDF SWIG types). pip cache was unavailable within the sandbox; dependency validation still passed. Browser tooling is the remaining acceptance blocker, not an application-test failure.


## M1 final browser certification — 2026-09-19

Result: PASS. Milestone M1 / Mode TEST / Status DONE. This certification supersedes the incomplete browser result above. M0 remains DONE and M2 remains TODO.

Browser verification:
- Google Chrome completed the required real-browser flow against the isolated temporary learner data directory `/var/folders/gx/n5qy94qd5xg4hv43mrd775mr0000gn/T/pdf-learning-os-m1-browser-8zovsikd`. The test used a disposable generated PDF and did not read or modify learner data. Safari was also used to inspect the initial Ready and empty-library state before the full Chrome flow.
- Verified the empty library, valid PDF import and importing/loading state, populated list, in-page details, and required M1 metadata.
- Re-importing the same bytes produced the approved duplicate response and an action to open the existing book; it did not create a second record or stored copy.
- Deletion required explicit confirmation. Cancel left the book present; confirmed deletion removed it. The book remained absent after page reload.
- Re-imported the PDF, restarted the backend against the same temporary data directory, reloaded the browser, and verified that the book and metadata persisted. A final confirmed deletion left the temporary library empty.
- Labels, controls, details navigation, confirmation controls, and keyboard interaction remained usable. No broken UI state, unexpected application error, or obvious browser runtime failure was observed. No browser automation framework or dependency was added.

Final acceptance:
- The previously recorded backend, frontend, migration, live HTTP, restart, storage-isolation, recovery, duplicate, deletion, and scope checks remain satisfied. The final repository review found no intervening production-code changes beyond the tested M1 implementation; `git diff --check` remains clean and repository `data/` remains absent.
- All fourteen recorded M1 acceptance criteria now pass. Source integrity is preserved, no M2 behavior or infrastructure was introduced, and no acceptance blocker remains.
- Defects found/fixed during final browser verification: none. Production code, tests, dependencies, and migrations were unchanged during finalization.
- Files changed during finalization: `TASKS.md` and `CHANGELOG.md` only. No commit or push performed.
- Non-failing warnings remain limited to the seven previously recorded upstream Starlette, AnyIO, and PyMuPDF warnings.


## Historical M2 task

Task: M2 — PDF Processing
Milestone: M2
Mode: TEST
Status: DONE
Approval: User explicitly approved the complete M2 plan for implementation on 2026-09-19.

Goal: implement FR-006–FR-011 only: exact per-page text extraction for machine-readable PDFs, bookmark/TOC extraction, physical page references, deterministic chapter mapping, correction of fallback structure, and durable processing states/errors. OCR and M3+ behavior remain out of scope.

Approved lifecycle: synchronous threadpool processing with `unprocessed`, `processing`, `processed`, and `failed`. Reprocessing keeps the last successful artifacts until a replacement commits; a failed reprocess preserves them. Startup marks interrupted attempts failed. Concurrent processing, deletion, and correction conflicts are rejected safely.

Approved persistence: Alembic revision `0002_pdf_processing` extends books with processing/error/timestamp/active-generation/TOC fields and adds pages and chapters with cascade ownership. Exact PyMuPDF `get_text("text", sort=False)` output is stored as immutable UTF-8 page artifacts under UUID-derived extraction generations; SQLite stores page references, hashes, counts, and structure. No API accepts or exposes paths.

Approved extraction: verify the stored original digest and structure before processing. Require at least 50 Unicode letters/digits in total and one page with at least 20; otherwise store `failed / ocr_required` and explain that OCR is unsupported. Never trim, normalize, reorder, summarize, or otherwise rewrite extracted page text.

Approved TOC and correction: validate bookmarks in source order, skip invalid/backward entries, normalize level jumps deterministically, derive inclusive ranges, and report available/partial/missing/invalid TOC state. Missing or unusable TOC yields one explicit `Full document` fallback. Only fallback/manual outlines can be replaced by ordered flat section titles and start pages; no AI chapter detection.

Approved interfaces: extend Book processing metadata; add `POST /books/{id}/process`, `GET /books/{id}/chapters`, and `PUT /books/{id}/chapters`; add an accessible processing/outline/fallback-correction panel to book details. No page reader is added.

Acceptance criteria:
1. Exact per-page UTF-8 artifacts match unsorted PyMuPDF output and retain 1-based physical page references.
2. Nested, partial, missing, and invalid TOCs map deterministically without fabricated source structure.
3. Valid fallback/manual corrections replace structure atomically; TOC structures remain read-only.
4. Image-only/sparse-text PDFs fail clearly as OCR-required without partial artifacts.
5. Processing and safe errors persist across restart; failed reprocessing preserves the last successful content.
6. Versioned filesystem/database switching and recovery follow committed active-generation state at every failure boundary.
7. Confirmed M1 deletion removes originals and all derived M2 data; rollback/recovery preserve ownership and path safety.
8. Existing M1 rows migrate to unprocessed without metadata or file changes, and all M1 behavior remains passing.
9. Frontend processing, success, failure, OCR, outline, correction, polling, focus, and stale-response states are accessible and tested.
10. No OCR, AI, reader, M3+, worker queue, cloud, or unapproved dependency/infrastructure is introduced.

Required CODE gates: backend pytest and pip check; frontend lint, Vitest, typecheck, and build. After implementation and automated verification, set Mode CODE / Status READY FOR TEST. Do not update CHANGELOG.md until formal TEST passes.

CODE verification — 2026-09-19:
- Implemented exact per-page PyMuPDF text extraction, physical page references, guarded UTF-8 generation storage, source-digest validation, deterministic OCR-required classification, bookmark normalization, inclusive nested ranges, and explicit fallback structure.
- Added durable processing lifecycle/error metadata, pages and chapters schema, Alembic revision `0002_pdf_processing`, SQLite foreign-key enforcement, synchronous process/chapters/correction APIs, and CORS PUT support. Existing M1 rows migrate to unprocessed without replacing the database.
- Extended UUID-owned storage, trash deletion, compensation, and startup recovery for processing attempts and versioned extracted generations. Ambiguous commits follow the fresh active-generation pointer; failed reprocessing preserves prior successful artifacts and manual corrections.
- Added the accessible frontend processing panel, durable error and OCR guidance, status polling, outline display, and flat fallback/manual correction editor. No page text reader, router, frontend dependency, or background worker was added.
- Backend `pytest`: PASS, 82 collected, 82 passed, 0 failed, 7 upstream warnings. Coverage includes exact artifacts, multi-page references, nested/partial/missing/invalid TOC, text thresholds, source changes, correction, reprocessing, ambiguous/failed commits, cleanup recovery, restart, delete cascade, migration, path isolation, and all M1 tests.
- Backend `.venv/bin/python -m pip check`: PASS, no broken requirements. The pip cache warning is environmental and non-failing.
- Frontend `npm run lint`: PASS. `npm run test -- --run`: PASS, 4 files and 32 tests. `npm run typecheck`: PASS. `npm run build`: PASS with Vite 7.3.6.
- `git diff --check`: PASS. Repository `data/` remains absent; tests used temporary databases, storage, PDFs, and extraction artifacts. No learner data was read or modified.
- No dependency versions changed. `CHANGELOG.md` remains unchanged. No commit or push performed.
- Non-failing warnings remain the existing Starlette HTTPX, AnyIO alias, and PyMuPDF SWIG deprecations.
- Formal MODE: TEST remains required for disposable live migration/API and real-browser processing, nested outline, fallback correction, OCR-required, reprocessing, restart persistence, and final deletion verification. M2 is READY FOR TEST, not DONE; M3 remains TODO.


## M2 final TEST certification — 2026-09-22

Result: PASS. Milestone M2 / Mode TEST / Status DONE. M0 and M1 remain DONE; M3 remains TODO.

Automated and migration verification:
- A fresh disposable data directory at `/private/tmp/pdf-learning-os-m2-final.erpLo2/library` was used for Alembic and all live checks. `python -m alembic current` was checked before migration, `python -m alembic upgrade head` completed, and the final current revision was `0002_pdf_processing (head)`.
- Backend `python -m pytest -q`: PASS, 82 collected, 82 passed, 0 failed, with the seven previously recorded upstream Starlette, AnyIO, and PyMuPDF warnings. `python -m pip check`: PASS, no broken requirements.
- Frontend `npm test -- --run`: PASS, 4 files and 32 tests. `npm run lint`, `npm run typecheck`, and `npm run build`: PASS; Vite 7.3.6 built 33 modules.

Live integration verification:
- Imported disposable nested-TOC, no-TOC, image-only, and unrelated control PDFs into the isolated library. Exact extracted UTF-8 bytes matched PyMuPDF `get_text("text", sort=False)` on all three nested-TOC pages; SQLite retained physical page numbers 1, 2, and 3 and matching SHA-256 values.
- Verified nested bookmark structure and inclusive ranges, explicit `Full document` fallback, atomic two-section manual correction, OCR-required failure without processed content, successful reprocessing, and persistence of processing states, TOC, OCR error, and manual structure across backend restart.
- Confirmed deletion of the three M2 books returned 204 and removed their original/extracted directories plus all page/chapter rows. Their old detail endpoints returned 404 with `book_not_found` / `Book not found.` before and after restart. The unrelated control book and external sentinel remained intact through those deletions; final isolated cleanup left zero books, pages, chapters, staging, trash, or processing artifacts.

Real-browser verification:
- Google Chrome completed the M2 flow against the same disposable library. Verified processed nested bookmarks with hierarchy and physical ranges, successful browser reprocessing, manual fallback correction to `Core Concepts` and `Applications`, correction persistence after reload, and the durable OCR-required guidance after reprocessing the image-only PDF.
- After deletion, browser refresh showed only the unrelated control book. After backend restart and page reload, none of the three deleted titles returned and the control book remained. Browser console inspection found no application errors; warnings came only from an unrelated installed extension.
- Local file selection through the Chrome extension was not required for the M2 gate because M1's real-browser import lifecycle is already certified; disposable fixture imports were performed through the verified local API. No Playwright package, browser framework, dependency, or product code was added.

Final acceptance:
- All ten M2 acceptance criteria pass. FR-006–FR-011 are verified, source integrity and physical page references are preserved, and no OCR, AI, reader, M3+, worker, cloud, or other unapproved scope was introduced.
- The repository learner database was not used: its SHA-256, size, and modification timestamp were identical before and after certification. All servers were stopped. No commit or push was performed.
- Defects found/fixed during TEST: none. Production code, migrations, tests, and dependencies were unchanged during TEST. Files changed during TEST: `TASKS.md` and `CHANGELOG.md` only.


## Historical M3 task

Task: M3 — Learning Goals
Milestone: M3
Mode: TEST
Status: DONE
Approval: User explicitly approved the complete M3 plan for implementation on 2026-09-22.

Goal: implement FR-012–FR-013 only: create one active learning goal with an optional description and associate 3–5 distinct existing books. Book analysis, AI, profiles, comparison, roles, paths, and M4+ remain out of scope.

Approved persistence: Alembic revision `0003_learning_goals` adds learning goals and a many-to-many goal/book association. Multiple goals may remain as inactive history, a partial unique index permits at most one active goal, association primary keys prevent duplicates, and book/goal foreign keys cascade without dangling rows.

Approved lifecycle: every new goal is active and must contain 3–5 books; creation atomically deactivates the prior active goal. No drafts, inactive-goal browsing, reactivation, deletion, or title/description editing are included. The active goal's complete book selection can be replaced atomically with another valid 3–5-book set.

Approved integrity: title is trimmed and limited to 1–200 characters; optional description is trimmed, blank-normalized to null, and limited to 2,000 characters. Missing, malformed, or duplicate book IDs fail the whole mutation. Any existing book is selectable regardless of processing status. Deleting a book in the active goal is blocked until it is replaced; inactive associations cascade on later book deletion.

Approved interfaces: add `POST /learning-goals`, `GET /learning-goals/active`, and `PUT /learning-goals/{id}/books`. Add an accessible frontend flow to create/view the active goal, select 3–5 existing books, replace its selection, and start a new goal with clear deactivation notice.

Acceptance criteria:
1. Goals with exactly three or five distinct existing books can be created and survive restart.
2. Creating a new goal atomically leaves it as the sole active goal and retains the prior goal inactive.
3. Invalid text, selection counts, duplicate/malformed IDs, and missing books are rejected without partial changes.
4. The active goal selection can be replaced atomically only with another valid 3–5-book set.
5. Unprocessed, failed, and processed books are selectable without triggering processing or analysis.
6. Deleting an actively selected book is blocked before database or filesystem mutation; deletion works after valid replacement.
7. Foreign keys prevent dangling relationships and allow inactive associations to cascade on book deletion.
8. Migration from a populated M2 database preserves books, pages, chapters, extraction metadata, and files.
9. Frontend creation, active display, selection bounds, replacement, busy/error/focus, and unknown-outcome states are accessible and tested.
10. All M1/M2 behavior remains passing and no M4+ behavior or new dependency is introduced.

Required CODE gates: backend pytest and pip check; frontend lint, Vitest, typecheck, and build; `git diff --check`. After implementation and automated verification, set Mode CODE / Status READY FOR TEST. Do not update CHANGELOG.md until formal TEST passes.

CODE verification — 2026-09-22:
- Added Alembic revision `0003_learning_goals`, learning-goal and association models, one-active-goal database enforcement, 3–5-book transactional validation, inactive history, active selection replacement, and safe book-deletion protection.
- Added `POST /learning-goals`, `GET /learning-goals/active`, and `PUT /learning-goals/{id}/books` with stable response contracts, explicit validation errors, shared library locking, persistence, and no processing prerequisite.
- Added the accessible Learning goal interface for creation, optional description, 3–5 existing-book selection, active-goal display, full selection replacement, new-goal deactivation warning, busy/error/focus states, and unknown-outcome refresh without mutation replay.
- Fresh isolated Alembic upgrade reached `0003_learning_goals (head)`. Migration coverage verifies populated M2 books, pages, chapters, and extraction metadata remain intact.
- Backend `pytest`: PASS, 98 collected, 98 passed, 0 failed, with the seven existing upstream warnings. Backend `python -m pip check`: PASS, no broken requirements.
- Frontend `npm test -- --run`: PASS, 6 files and 43 tests. `npm run lint`, `npm run typecheck`, and `npm run build`: PASS; Vite built 35 modules.
- `git diff --check`: PASS. Tests and migration checks used temporary data only; no learner data was read or modified. No dependency changes, commit, or push were performed.
- `CHANGELOG.md` remains unchanged. Formal MODE: TEST remains required for isolated live API/restart/deletion checks and real-browser creation, validation, replacement, new-goal activation, persistence, and protected deletion. M4 remains TODO.

## M3 final TEST certification — 2026-09-22

Result: PASS. Milestone M3 / Mode TEST / Status DONE. M0–M2 remain DONE and M4 remains TODO.

Automated and migration verification:
- Backend `pytest`: PASS, 98 collected, 98 passed, 0 failed, with seven existing upstream Starlette, AnyIO, and PyMuPDF warnings. `python -m pip check`: PASS, no broken requirements.
- Frontend `npm test -- --run`: PASS, 6 files and 43 tests. `npm run lint`, `npm run typecheck`, and `npm run build`: PASS; Vite 7.3.6 built 35 modules.
- Fresh and populated-M2 temporary databases both reached `0003_learning_goals (head)`. Repeated upgrade to head was safe. Existing books, pages, chapters, extraction metadata, original PDF bytes, and page artifacts remained unchanged.
- Verified the exact six-table M3 schema, composite association primary key, cascading goal/book foreign keys, and partial unique active-goal index. No M4+ schema exists.

Live integration verification:
- Used `/private/tmp/pdf-learning-os-m3-final.LQpcSk/live` only. Imported six disposable PDFs, processed an unrelated control book, created a three-book goal, restarted the backend, and confirmed the goal and associations persisted.
- Replaced the active selection with five books; rejected two, six, duplicate, and missing-ID selections with the approved status/code responses. Creating a second goal retained the first inactive and left exactly one active goal.
- Deleting an actively selected book returned 409 `book_in_active_goal` without changing the book. After a valid replacement, deletion returned 204, left no dangling associations, and preserved the unrelated book's M2 processing row, page manifest, chapter structure, and extracted content.

Real-browser verification:
- Google Chrome verified active-goal loading, title and optional description entry, visible 3–5 validation, three- and five-book selection, active display, selected-book display, selection replacement, new-goal deactivation warning, and creation of a new sole active goal.
- A fresh browser tab confirmed persistence. The browser showed the approved deletion conflict for a selected book, then allowed deletion after that book was removed from a still-valid selection; the active goal remained valid afterward.
- Keyboard focus/navigation and mutation focus restoration were usable. No application console errors occurred; console warnings/errors were limited to unrelated installed Chrome extensions.

Final acceptance:
- All M3 acceptance criteria and FR-012–FR-013 pass. No AI, analysis, profiles, comparison, roles, learning path, reader, translation, recall/quiz, mastery/progress, or M4+ behavior was introduced.
- Defects found/fixed during TEST: none. Production code, migration, dependencies, and tests were unchanged during TEST. Files changed during TEST: `TASKS.md` and `CHANGELOG.md` only.
- All temporary test data was isolated from learner data, and both servers were stopped. No commit or push was performed.


## Historical M4 task

Task: M4 — Book Profiles
Milestone: M4
Mode: TEST
Status: DONE
Approval: User explicitly approved the complete M4 plan for implementation on 2026-09-22.

Goal: implement FR-014–FR-015 only: store one current, manually editable, book-level profile per book containing domain, difficulty, prerequisites, main topics, theory/practice orientation, strengths, weaknesses, and suggested use. M5 comparison, roles, AI analysis, learning paths, and later behavior remain out of scope.

Approved ownership: a book has zero or one profile, keyed by `book_id` with cascading deletion. M4 keeps no versions or profile history. Profiles are global book metadata, not learning-goal-specific; `suggested_use` is general guidance, while goal-specific use and roles remain future M5/M6 decisions.

Approved fields: nullable trimmed `domain` (max 200); nullable `difficulty` enum `beginner | intermediate | advanced`; ordered unique lists for `prerequisites` (max 25 items, 200 characters each), `main_topics` (max 50 items, 200 characters each), `strengths` and `weaknesses` (max 20 items each, 500 characters each); nullable `orientation` enum `theory_heavy | balanced | practice_heavy`; nullable trimmed `suggested_use` (max 2,000); UTC created/updated timestamps. Lists are stored as deterministic JSON arrays in SQLite TEXT columns and exposed as arrays. At least one field must be populated to create a profile; null and empty-list values explicitly represent unknown/not recorded.

Approved provenance: every FR-014 field has a server-owned nullable source value from `manual | ai_generated | ai_assisted | derived`. The M4 API never accepts provenance and sets each populated field to `manual`; empty fields have null source. A later assisted workflow may set other values without a schema redesign. Responses expose a per-field provenance map, and the UI labels values as manually entered. No profile claim is represented as extracted PDF source.

Approved AI/content boundary: M4 is manual-first and adds no AI provider, model call, automatic inference, page-text read, or chapter analysis. Any existing catalog book may have a profile regardless of processing status or local-file availability. Processing validation belongs to future automated analysis, not FR-014/015.

Approved interfaces: `GET /books/{book_id}/profile` returns `{profile: null}` for an existing book without a profile and 404 for a missing book. `PUT /books/{book_id}/profile` performs a complete validated create-or-replace and returns the current profile. Routes remain thin; service mutations share the library lock with deletion. No PATCH, history, analysis, comparison, or goal-profile endpoint is added.

Approved frontend: add an accessible profile panel to book details. It supports absent/loading/error/retry states, read-only display with provenance labels, create/edit/cancel, selects for difficulty/orientation, line-separated textareas for list fields, client/server validation, busy/status/focus handling, and unknown-outcome reload without mutation replay. It adds no comparison or role UI.

Data/schema: Alembic revision `0004_book_profiles` adds only `book_profiles`, preserving every M1–M3 table and file. `book_id` is the primary key and an `ON DELETE CASCADE` foreign key to books. Database checks cover scalar bounds, enums, provenance values, and source/value null coherence where practical; service validation covers JSON arrays, counts, item lengths, trimming, and case-insensitive duplicates. Runtime schema head becomes `0004_book_profiles`.

Acceptance criteria:
1. An existing book can have zero or one current profile; absent and populated states persist across restart.
2. Complete PUT creates or replaces the profile atomically, preserves `created_at`, advances `updated_at`, and never creates duplicates or history rows.
3. Every scalar, enum, list count, item length, blank item, and case-insensitive duplicate rule is enforced without partial writes.
4. All eight fields round-trip in stable JSON shapes with explicit null/empty defaults and per-field provenance.
5. M4 writes only `manual` provenance for populated fields and never accepts client-supplied source claims.
6. Unprocessed, failed, processed, and missing-local-file catalog books can be profiled without reading M2 content or invoking AI.
7. Book deletion cascades its profile without dangling data or changing existing storage cleanup behavior.
8. A populated M3 database upgrades to `0004_book_profiles` without changing books, processing artifacts, goals, or associations.
9. Frontend view/create/edit/cancel/save/validation/error/busy/focus/unknown-outcome flows are accessible and tested.
10. M1–M3 regressions pass, M5 remains unimplemented, no dependency is added, and `CHANGELOG.md` remains unchanged until formal TEST.

Required CODE gates: backend pytest and pip check; frontend lint, Vitest, typecheck, and build; isolated migration verification; `git diff --check`. After implementation set M4 to Mode CODE / Status READY FOR TEST, not DONE.

CODE verification — 2026-09-22:
- Implemented Alembic revision `0004_book_profiles`, the one-to-one cascading book-profile model, strict schemas, manual-provenance normalization, atomic complete upsert, absent/read APIs, and shared-lock service integration. Runtime schema readiness now requires `0004_book_profiles`.
- Added an accessible profile panel to book details with absent/loading/error/retry, read/create/edit/cancel, structured selects and line-based lists, provenance labels, client/server validation, busy/status/focus behavior, and unknown-outcome reload without mutation replay.
- Added backend coverage for absent/create/read/update, normalization and structured validation, server-owned provenance, restart persistence, missing books/files, processing-independent behavior, deletion cascade, and populated-M3 migration. Added frontend transport and component coverage and updated library/schema regressions.
- Updated `ARCHITECTURE.md` and `README.md` for the M4 storage, service, API, frontend, provenance, migration, and scope boundaries. No dependency or lockfile changed.
- Targeted checks: backend profile/library/goal suite PASS (65 tests); frontend profile transport/panel/library suite PASS (20 tests); isolated migration upgrade PASS; frontend typecheck PASS.
- Full CODE gates: backend `pytest -q` PASS (116 tests, 7 existing upstream warnings) and `python -m pip check` PASS; frontend `npm test -- --run` PASS (8 files, 52 tests), lint PASS, typecheck PASS, and build PASS (Vite 7.3.6, 37 modules). Fresh isolated Alembic upgrade/current reached `0004_book_profiles (head)` and `git diff --check` passed.
- Known non-failing warnings are unchanged: upstream Starlette HTTPX, AnyIO alias, PyMuPDF SWIG deprecations, and the environment-only unwritable pip cache warning. No known M4 implementation issue remains.
- Formal MODE: TEST remains required; M4 is READY FOR TEST, not DONE. `CHANGELOG.md` remains unchanged, no commit or push was performed, and M5 remains TODO.

## M4 final TEST certification — 2026-09-22

Result: PASS. Milestone M4 / Mode TEST / Status DONE. M0–M3 remain DONE and M5 remains TODO.

Migration and automated verification:
- Fresh and repeated isolated Alembic upgrades reached `0004_book_profiles (head)`. The populated-M3 upgrade preserved books, pages, chapters, learning goals, associations, original PDF bytes, and extracted page artifacts.
- Verified the seven expected M0–M4 tables only, the one-to-one `book_profiles` primary key, cascading book foreign key, nullable/bounded scalars, enums, deterministic JSON-list storage, provenance constraints, and value/source coherence checks. No M5+ schema exists.
- Backend `pytest -q`: PASS, 116 collected, 116 passed, 0 failed, with seven existing upstream Starlette, AnyIO, and PyMuPDF warnings. `python -m pip check`: PASS with no broken requirements; the unwritable pip-cache notice remains environmental and non-failing.
- Frontend `npm test -- --run`: PASS, 8 files and 52 tests. `npm run lint`, `npm run typecheck`, and `npm run build`: PASS; Vite 7.3.6 built 37 modules. `git diff --check`: PASS.

Live integration verification:
- Used only `/private/tmp/pdf-learning-os-m4-resume.hs6DFy/live`. Imported four disposable books, confirmed the absent profile state, created/read a complete eight-field profile, replaced it atomically, restarted the backend, and confirmed exact values, timestamps, associations, and manual provenance persisted.
- Duplicate-field and client-forged-provenance updates returned 422 and left the previous complete profile byte-for-byte unchanged. Missing-book profile lookup returned 404 `book_not_found`.
- Deleted the profiled book and confirmed its book/profile rows and owned files were gone. An unrelated profile, original PDF hash, processed M2 page/chapter data, active M3 goal, and three unrelated books remained unchanged. M1 list/details/delete, M2 process/chapters, and M3 create/active-goal APIs remained functional.

Real-browser verification:
- Google Chrome verified the absent state, complete creation with all eight fields, manual provenance labels, reload persistence, multi-field full replacement, and replacement persistence after another reload.
- Duplicate-topic validation was announced without saving or destroying the prior valid profile. Tab navigation reached the profile action and Enter opened the editor; labeled inputs, selects, textareas, status, alert, focus restoration, and confirmation controls remained keyboard-accessible.
- Browser deletion removed the profiled book and profile panel immediately; reload confirmed it did not return, while unrelated books and the active goal remained. The old profile URL returned 404 and SQLite contained no dangling profile row.
- No application console/runtime errors occurred. Observed console warnings/errors came only from installed Chrome extensions; Vite and React emitted normal development messages.

Final acceptance:
- All ten M4 acceptance criteria and FR-014–FR-015 pass. M4 remains manual-first and adds no AI provider call, automatic generation, comparison, overlap, book roles, learning-path behavior, RAG, embeddings, dependency, or M5+ functionality.
- Defects found/fixed during TEST: none. Production code, migration, dependencies, and tests were unchanged during TEST. Files changed during TEST: `TASKS.md` and `CHANGELOG.md` only.
- Learner data was not read or modified. All test PDFs, databases, extracted artifacts, profiles, and goals were isolated disposable data. No commit or push was performed.

## Historical M5 task

Task: M5 — Book Comparison
Milestone: M5
Mode: TEST
Status: DONE
Approval: User approved the complete M5 plan in this conversation.

Goal: FR-016–018 only: goal-specific comparison of 3–5 selected books with deterministic profile matching and explicitly manual roles, relevance, rationale, and optional depth/practice assessments. No M2 content read, AI, semantic matching, scoring, or M6 sequencing.

Approved readiness: active goal, 3–5 existing selected books, each with an M4 profile and nonblank topics. Other missing fields remain unknown; empty prerequisites mean not recorded. Normalize topics/prerequisites by whitespace collapse and Unicode casefold, preserving originals. Coverage and pairwise intersections/differences are derived; difficulty uses existing ordinal categories; orientation is distinct from actual practice content.

Approved judgments: every selected book has exactly one core/selected_chapters/reference/skip_for_now role and 1–2,000-character rationale. Required relevance category high/partial/low/unknown and 1–1,000-character explanation. Optional depth overview/working_detail/deep_treatment and practice limited/some/substantial each require an explanation. Focus topics (max 50) must belong to that book, and selected_chapters requires at least one. Optional unique evidence references (max 20) target populated profile fields, own topics, or own pairwise facts. Provenance is server-owned and manual for judgments; each book requires explicit review confirmation.

Approved persistence: 0005_book_comparisons adds one snapshot per goal and snapshot-book membership. Capture goal/profile inputs, provenance, deterministic results, algorithm version, timestamps, revision, and canonical input fingerprint. GET is read-only; PUT atomically replaces complete snapshot after readiness, token, revision, and judgment validation. Profile/selection changes mark saved data stale; review carries judgments by book ID without silently replacing them. Inactive goals are read-only. Deleting a book atomically deletes all affected snapshots after existing deletion guards; unrelated data remains intact.

Approved API: GET/PUT /learning-goals/{goal_id}/comparison. Envelope: goal_id, is_active, readiness/issues, input_token, current preview, saved snapshot, stale and stale_reasons. PUT: input_token, expected_revision, exact selected books with all manual fields and reviewed=true. Missing goal 404; inactive/unready/input-changed/revision-conflict 409; malformed fields/references 422; safe storage failures 503.

Approved UX: comparison within active goal; readiness links open existing profile editor, compact overview plus book details and expandable coverage/pairs, labeled provenance and unknowns, complete editing, explicit stale review, keyboard/status/focus/error/busy handling. Refresh after goal/profile changes and window focus; preserve drafts and reload unknown outcomes without replay. Warn deletion removes affected comparisons.

Acceptance criteria:
1. Deterministic comparisons work for three and five ready selected books.
2. Missing profiles/topics block comparison; other missing facts remain unknown.
3. All seven dimensions have accurate source labels without semantic claims.
4. Every saved book has one manual role and rationale; selected_chapters has valid focus topics.
5. Provenance, computed results and captured inputs cannot be forged by clients.
6. Atomic saves persist across restart and reject stale inputs/concurrent overwrites.
7. Changes require explicit review and preserve the old snapshot until replacement.
8. Book deletion removes affected snapshots with rollback and unrelated data intact.
9. Accessible UI covers readiness/edit/cancel/error/busy/focus/unknown outcomes.
10. Migration preserves M1–M4 data and all existing regressions pass.
11. No new dependencies, AI, M6 stages/order/chapter selections/study plans or later scope.

Implementation/tests: migration/models/typed contracts/pure comparisons; shared-lock service/routes/deletion; frontend transport/panel/refresh integration; documentation. Verify normalization and unknowns, all dimensions/roles/evidence, atomicity/conflicts, stale/review, restart/deletion, populated M4 migration, frontend flows and full backend pytest/pip check, frontend lint/test/typecheck/build, and diff check using temporary data only. CODE ends READY FOR TEST; CHANGELOG remains unchanged until formal TEST.

CODE implementation and verification — 2026-09-22:
- Added Alembic revision `0005_book_comparisons`, the one-per-goal snapshot model and exact snapshot-book membership table. Runtime readiness now requires this head. Fresh/repeated upgrades, populated-M4 preservation, database constraints, downgrade on disposable data, cascading membership cleanup, and restart persistence are covered by isolated tests.
- Added strict comparison schemas, deterministic Unicode-whitespace/casefold normalization, exact topic/prerequisite matching, seven-dimension previews, canonical input fingerprints, typed snapshot validation, optimistic input/revision checks, and atomic complete replacement. Saved manual roles, rationales, relevance, optional depth/practice, focus topics, evidence references, review confirmation, and server-owned provenance are validated without reading M2 content or invoking AI.
- Added thin GET/PUT comparison routes, active/inactive/readiness behavior, stale snapshot reporting, safe storage errors, and transactional deletion of every affected snapshot after the existing active-goal deletion guard. Rollback, concurrent writes, selection/profile changes, no-op timestamp invalidation, reprocessing independence, unrelated data preservation, malformed/corrupt storage, and client forgery are covered.
- Added the active-goal comparison UI with readiness links, source labels, explicit unknowns, overview/details, exact-match limitations, create/edit/cancel/save, stale review and judgment carryover, invalid-reference flags, profile/goal/focus refreshes, busy/error/status/focus handling, responsive presentation, and unknown-outcome reload without mutation replay. Book deletion warns that affected saved comparisons are removed.
- Updated `ARCHITECTURE.md` and `README.md` for M5 schema, API, matching, provenance, invalidation, UI, deletion, migration, and M6 handoff boundaries. No dependency or lockfile changed. `CHANGELOG.md` remains unchanged pending formal TEST.
- Focused defects fixed during CODE verification: TypeScript runtime-validator narrowing was corrected; M5 table expectations were added to M1/M2 migration regressions; ambiguous storage-error saves now reload authoritative comparison state while preserving the draft; stored snapshots now revalidate membership, profile ownership, evidence targets, and server-owned provenance. Regression coverage was added for each affected behavior.
- Full backend gate: `.venv/bin/python -m pytest -q` PASS — 150 passed, 0 failed; `.venv/bin/python -m pip check` PASS — no broken requirements.
- Full frontend gate: `npm test -- --run` PASS — 10 test files, 68 tests; `npm run lint` PASS; `npm run typecheck` PASS; `npm run build` PASS with Vite 7.3.6 and 40 transformed modules.
- `git diff --check` PASS. Scope inspection confirms M1–M4 regressions remain passing and no AI/provider, RAG, embedding/vector, semantic matching, chapter selection/order, dependency graph, learning path, stage, schedule, or study-plan behavior was introduced.
- Known non-failing warnings are unchanged upstream/environment notices: seven backend warnings (Starlette HTTPX deprecation, AnyIO portal alias, and PyMuPDF SWIG deprecations) plus the unwritable pip-cache notice. No known M5 implementation blocker remains.
- Formal isolated live HTTP and real-browser certification remain for MODE: TEST. M5 is READY FOR TEST, not DONE. No learner data was used, no commit or push was performed, and M6 remains TODO.

## M5 final TEST certification — 2026-09-22

Result: PASS. Milestone M5 / Mode TEST / Status DONE. M0–M4 remain DONE and M6 remains TODO.

Migration and automated verification:
- Fresh and repeated isolated Alembic upgrades reached `0005_book_comparisons (head)`. The populated-M4 upgrade/downgrade test preserved all M1–M4 books, pages, chapters, profiles, goals, associations, original PDFs, and extracted artifacts.
- Verified exactly the expected M0–M5 tables: `books`, `pages`, `chapters`, `learning_goals`, `learning_goal_books`, `book_profiles`, `book_comparisons`, `book_comparison_books`, and `alembic_version`. Comparison primary keys, positive-revision/fingerprint checks, snapshot ownership, composite membership uniqueness, cascading foreign keys, and `PRAGMA foreign_key_check` passed. No M6+ schema exists.
- Backend `.venv/bin/python -m pytest -q`: PASS — 150 passed, 0 failed, with seven unchanged upstream Starlette, AnyIO, and PyMuPDF warnings. `.venv/bin/python -m pip check`: PASS — no broken requirements; the environment-only unwritable pip-cache notice remains non-failing.
- Frontend `npm test -- --run`: PASS — 10 files and 68 tests. `npm run lint`, `npm run typecheck`, and `npm run build`: PASS; Vite 7.3.6 transformed 40 modules. `git diff --check`: PASS.
- Automated coverage explicitly passed for ready three- and five-book comparisons; missing/incomplete profiles; exact Unicode whitespace/casefold normalization; disjoint, partial, and shared topic sets; difficulty, prerequisites, orientation versus practice, relevance, all four roles, rationale/review requirements, focus topics, evidence validation, server-owned provenance, atomicity, restart persistence, stale profile/selection inputs, reprocessing independence, concurrent/ambiguous saves, rollback, deletion cleanup, and M1–M4 regressions.

Live HTTP integration:
- Used only `/private/tmp/pdf-learning-os-m5-test.xnIEps`. Created five disposable PDFs, complete M4 profiles, one active goal, processed content, and reviewed comparisons. Generated/read revision 1, restarted the backend, and confirmed the complete snapshot persisted exactly.
- Verified normalized overlap and no-overlap pairs, difficulty/prerequisite differences, profile orientation distinct from manual practice, manual relevance/depth/practice, three roles with rationales, optional evidence, and server-owned manual provenance. Forged provenance and invalid evidence returned 422 and left the saved snapshot unchanged.
- Reprocessing left the comparison current as approved. A profile edit marked revision 1 stale; its old input token returned 409 `comparison_inputs_changed`; explicit review produced current revision 2. A goal-selection change retained revision 2 as stale; an exact reviewed replacement produced revision 3.
- Changed the selection again so a snapshot member was no longer active, deleted that book, and confirmed the affected comparison and memberships were removed transactionally. Four unrelated books, their profiles, the processed book/pages/chapters, active goal, original files, and M1/M2/M3 APIs remained intact. The deleted book returned 404 and database foreign-key checks remained clean.

Real-browser verification:
- Google Chrome against the same isolated data verified a ready three-book comparison, side-by-side topic/difficulty/prerequisite/orientation/overlap facts, exact-match limitation text, explicit unknowns, and separately labeled profile inputs, derived facts, and manual judgments. No dependency order, stages, chapter sequence, study plan, or other M6 UI appeared.
- Created a complete comparison using CORE, SELECTED CHAPTERS with a valid focus topic, and REFERENCE; each had a rationale and relevance explanation, with optional depth/practice assessments and evidence. Native required-field validation blocked an incomplete save without losing the draft. The UI saved revision 1 and visibly retained all roles, rationales, and provenance.
- Edited a selected book profile in Chrome. The comparison immediately showed the saved snapshot as stale while preserving it. Review carried judgments by book ID, reset all review confirmations, exposed the new derived topic, and saved revision 2 only after explicit confirmation.
- Replaced one goal book. The UI showed revision 2 stale, excluded the removed book, retained matching judgments, started the new book unclassified, and saved reviewed revision 3. A full browser reload preserved revision 3, the revised three-book selection, all roles, and rationales.
- Keyboard Tab reached comparison controls; native labeled controls, headings, table semantics, details disclosure, status/error regions, and focus restoration were exposed through Chrome accessibility state. No application console/runtime error occurred. Console warnings/errors came only from installed Chrome extensions; Vite/React emitted normal development messages, including one transient Vite reconnect notice during tool-driven tab refresh.

Final acceptance:
- All eleven M5 acceptance criteria and FR-016–FR-018 pass. M5 remains deterministic/manual-first and adds no AI provider call, automatic classification, semantic matching, score, RAG, embedding, vector database, dependency order, stage, chapter sequence, learning path, `STUDY_PLAN.md`, or M7+ behavior.
- Defects found/fixed during formal TEST: none. Production code, migration, dependencies, and tests were unchanged during TEST. Files changed during TEST: `TASKS.md` and `CHANGELOG.md` only.
- Learner data was not read or modified. All databases, PDFs, profiles, goals, processed artifacts, and comparisons were isolated disposable data. Both test servers and the isolated Chrome tab were stopped/closed. No commit or push was performed.

## Active Task

Task: M5.5 — Library Intelligence & Curriculum Triage
Milestone: M5.5
Mode: TEST
Status: DONE
Approval: User approved the decision-complete M5.5 plan in this conversation.

Goal: Add a compact deterministic/manual-first intelligence and triage workflow for 30–100 books without weakening M3's confirmed 3–5-book invariant or M5's reviewed comparison contract.

Approved design:
- Persist one editable curriculum-triage session with 0–many candidate books; retain applied sessions as read-only history.
- Require 1–25 target topics, with optional target domain and difficulty ceiling. Whole-library scope is a snapshot that requires explicit synchronization after library membership changes.
- Compute library maps, bibliographic duplicate/edition candidates, exact recorded-topic overlap, explicit prerequisite providers, and a score-free rule-based shortlist on demand from M1 metadata and M4 profiles only.
- Persist library-wide pair reviews but never auto-delete or merge books.
- Require explicit confirmation of 3–5 ready books, at least one CORE/SELECTED role, no LATER role, and complete M5-compatible reviewed judgments.
- Atomically create the new active M3 goal, revision-1 M5 comparison, and applied triage result under the existing shared lock.
- Add Alembic `0006_library_intelligence`; preserve all M1–M5 rows and files. No AI, PDF-text/TOC analysis, semantic matching, M6 sequencing, schedule, or study-plan artifact.

Acceptance criteria and test scope are the approved plan from this conversation: fresh/repeated/populated-M5 migrations; 30/100-book map behavior; duplicate/edition review; prerequisite and overlap evidence; deterministic shortlist and manual override; staleness/revisions; atomic confirmation/rollback; deletion integrity; accessible frontend workflows; full M1–M5 regression and quality gates.

CODE completion must set Mode CODE / Status READY FOR TEST, record exact gate counts and warnings, leave `CHANGELOG.md` unchanged, and stop before live HTTP/browser certification.

CODE implementation and verification — 2026-09-23:
- Added FR-048–FR-052 and the revised M5.5/M6/M6.5 roadmap to `PROJECT.md` and `SOFTWARE_REQUIREMENTS.md`; documented architecture, migration, API, matching limits, triage workflow, atomic handoff, deletion behavior, and usage in `ARCHITECTURE.md` and `README.md`. `CHANGELOG.md` remains unchanged pending formal TEST.
- Extracted M5's canonical JSON, Unicode whitespace/casefold normalization, normalized-key, and set-comparison primitives into `backend/app/services/profile_matching.py`; existing M5 output and regression behavior remain passing.
- Added Alembic `0006_library_intelligence`, curriculum-triage/relation-review models, strict request and response schemas, thin intelligence/triage routes, application registration, and runtime-head enforcement. Fresh and repeated isolated upgrades reached `0006_library_intelligence (head)`; populated-M5 preservation, disposable downgrade, constraints, single-draft index, cascades, and schema expectations are covered.
- Added batched library-map facts, private exact-duplicate invariant reporting, exact bibliographic duplicate/edition candidates, recorded-topic redundancy/unique/complementary facts, exact prerequisite providers, persisted sorted-pair learner reviews, stable pagination, and separate per-book relationship counts. Synthetic 30- and 100-book tests verify stable bounded output, no N+1 queries, and record the local 100-book map timing without a flaky threshold.
- Added persisted triage creation/history/replacement, whole-library and selected candidate scopes, fingerprints, explicit synchronization, revision/input conflicts, deterministic evidence bands and score-free shortlist, partial-evidence behavior, duplicate preference, profile/review/library staleness, and atomic confirmation into a new M3 goal plus revision-1 M5 snapshot. Book deletion preserves the active-goal guard, cleans cascaded reviews/memberships/comparisons, and invalidates only affected applied triage history.
- Added typed frontend transport/runtime validation and a collapsible Library Intelligence workflow with compact grouped map, search/readiness/domain/topic/difficulty/orientation/processing/candidate filters, profile-readiness queue, paginated duplicate/overlap/prerequisite review, explicit matching limitations, draft replacement/synchronization/read-only history, shortlist/manual override, full M5-compatible judgments, stale/error/busy/status/focus handling, and unknown-outcome reload without mutation replay or draft loss. The library refreshes active-goal state after application and warns about deletion impact.
- Files added: `backend/app/api/curriculum_triage.py`, `backend/app/api/library_intelligence.py`, `backend/app/models/library_intelligence.py`, `backend/app/schemas/library_intelligence.py`, `backend/app/services/curriculum_triage.py`, `backend/app/services/library_intelligence.py`, `backend/app/services/profile_matching.py`, `backend/migrations/versions/0006_library_intelligence.py`, `backend/tests/test_library_intelligence.py`, `frontend/src/api/libraryIntelligence.ts`, `frontend/src/api/libraryIntelligence.test.ts`, `frontend/src/features/intelligence/LibraryIntelligence.tsx`, and `frontend/src/features/intelligence/LibraryIntelligence.test.tsx`.
- Existing files updated: `PROJECT.md`, `SOFTWARE_REQUIREMENTS.md`, `ARCHITECTURE.md`, `README.md`, `TASKS.md`, backend migration readiness/application registration/M5 comparison/deletion services and migration regressions, plus frontend library integration and styles. No dependency or lockfile changed.
- Defects fixed during CODE verification: canonical bibliographic pair output was stabilized; recommendation prerequisite selection was restricted to shortlisted direct books; unreviewed probable duplicates were prevented from being auto-selected together; relationship counts were separated; strict response validation exposed and corrected candidate/map shape differences; frontend native form validation coverage and duplicate checkbox queries were corrected; unknown outcomes now preserve triage editors; and the M1-to-head processing migration regression was updated for the approved M5.5 tables. A full-suite failure from that stale table expectation was rerun successfully.
- Full backend gate: `.venv/bin/python -m pytest -q` PASS — 163 passed, 0 failed; `.venv/bin/python -m pip check` PASS — no broken requirements. Focused M5.5 suite: 13 passed.
- Full frontend gate: `npm test -- --run` PASS — 12 files, 76 tests; `npm run lint` PASS; `npm run typecheck` PASS; `npm run build` PASS with Vite 7.3.6 and 42 transformed modules.
- `git diff --check` PASS. Scope inspection confirms M1–M5 regressions remain passing and no AI/provider, full-PDF/TOC analysis, fuzzy or semantic matcher, RAG, embedding/vector store, graph, M6 dependency order/stage/chapter selection, 90-day schedule, or study-plan artifact was introduced.
- Known non-failing warnings remain the seven upstream backend notices (Starlette HTTPX deprecation, AnyIO portal alias, and PyMuPDF SWIG deprecations) plus the environment-only unwritable pip-cache notice. No known implementation blocker remains.
- Formal isolated live HTTP and real-browser certification remain for MODE: TEST. M5.5 is READY FOR TEST, not DONE. No learner data was used, and no commit or push was performed. M6 remains TODO.

Formal TEST certification — 2026-09-23:
- Result: PASS. Milestone M5.5 / Mode TEST / Status DONE. M0–M5 remain DONE; M6 and M6.5 remain TODO.
- Migration PASS: fresh and populated-M5 disposable databases upgraded to `0006_library_intelligence (head)`; repeated upgrade was idempotent; existing M1–M5 rows survived unchanged; expected M5.5 tables, checks, cascading foreign keys, and partial single-draft index were present; `PRAGMA foreign_key_check` returned no rows; no M6 schema was introduced.
- Backend quality gate PASS: 163 passed, 0 failed; `python -m pip check` reported no broken requirements. Library-map, duplicate/edition, exact topic redundancy, prerequisite-provider, triage/shortlist, staleness/conflict, atomic confirmation, rollback, persistence, concurrency, deletion, migration, and M1–M5 regression coverage passed.
- Frontend quality gate PASS: 12 Vitest files / 76 tests; lint, typecheck, and production build passed with Vite 7.3.6 and 42 transformed modules. `git diff --check` passed.
- Scale PASS: synthetic 30- and 100-book maps returned every book in stable order with at most three SELECT statements, paginated pair results capped at 25, and bounded pair totals. The isolated 100-book map request measured 0.059439 seconds on the supported local toolchain; the live 32-book map measured 0.010968 seconds. These are observations, not product thresholds; no Redis, worker, graph, vector, or cache infrastructure was required.
- Isolated live HTTP PASS: imported 32 distinct disposable PDFs and rejected an exact-byte duplicate with 409; recorded 30 ready, one missing-profile, and one missing-topic case; identified probable duplicates, related editions, exact-topic equivalence/complementarity, exact prerequisite providers, and an unresolved prerequisite without exposing hashes or inventing semantic matches. A relation review persisted, while processing and M5 comparison changes correctly did not stale triage.
- Restart, staleness, and conflicts PASS: persisted map/reviews/goal/comparison/triage data survived backend restart; a relevant profile edit marked the whole-library draft stale; the old token and stale revision were rejected; explicit synchronization advanced the revision; the stale snapshot remained reviewable; invalid all-reference confirmation left the prior active goal unchanged.
- Atomic application and deletion integrity PASS: exact five-book HTTP confirmation and exact three-book Chrome confirmation each produced a new active M3 goal and revision-1 nonstale M5 comparison. Active-book deletion remained protected; unrelated deletion preserved the comparison; affected inactive comparison snapshots were removed; applied whole-library history was invalidated when appropriate; unrelated books/data remained intact; final foreign-key checks were clean.
- Google Chrome PASS against isolated disposable data: opened a usable 31-book grouped map; exercised search, readiness, and grouping filters; reviewed a probable duplicate as a related edition without deletion; inspected exact overlap/complementarity and provider/unresolved prerequisite evidence; used the profile-readiness queue; created a deterministic source-labeled shortlist; verified explicit CORE/SELECTED/REFERENCE/LATER presentation; observed profile-change staleness; explicitly synchronized and confirmed three books; reloaded to verify the active goal, applied history, review, and revision-1 M5 snapshot. Native validation preserved the prior goal, keyboard focus order worked, no M6 path/stage/chapter-order/90-day UI appeared, and no application console warning/error occurred. Unrelated Chrome-extension warnings were ignored.
- TEST defect fixed: the triage UI now states explicitly that CORE, SELECTED, and REFERENCE are included in Books Now while unselected candidates are LATER. Added a focused frontend regression assertion, then reran the complete backend/frontend quality gates successfully.
- Scope PASS: M5 deterministic comparison and the M3 3–5 active-set invariant remain intact; large candidate membership remains separate. No AI/provider call, full-PDF LLM submission, semantic matcher, autonomous agent, RAG, embedding, vector database, M6 dependency order/stage/chapter sequence, 90-day schedule, `STUDY_PLAN.md`, M7+ behavior, new dependency, commit, or push was introduced.
- Files changed during TEST: `frontend/src/features/intelligence/LibraryIntelligence.tsx`, `frontend/src/features/intelligence/LibraryIntelligence.test.tsx`, `TASKS.md`, and `CHANGELOG.md`. All databases, PDFs, goals, profiles, comparisons, triages, browser build files, and integration scripts were confined to `/private/tmp`; learner data was not read or modified. Isolated servers and the Chrome tab were stopped/closed.
- Remaining non-failing warnings: seven upstream backend notices (Starlette HTTPX deprecation, AnyIO portal alias, and PyMuPDF SWIG deprecations), one pytest `record_property`/xUnit2 notice from the explicit timing capture, the environment-only unwritable pip-cache notice, and unrelated Chrome-extension console warnings. No M5.5 blocker remains.
