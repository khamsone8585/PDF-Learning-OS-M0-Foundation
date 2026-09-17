# TASKS.md — PDF Learning OS

Status: TODO / PLANNED / IN PROGRESS / BLOCKED / READY FOR TEST / DONE

## M0 — Repository Foundation
**Status:** DONE

Create React+TS+Vite frontend, FastAPI backend, SQLite, frontend tests, backend tests, and `GET /health` integration. No AI or PDF feature yet.

## M1 — Local PDF Library
**Status:** TODO

Import, save, list, open details, and delete local PDFs.

## M2 — PDF Processing
**Status:** TODO

Extract metadata, page text, TOC, chapter/page mapping, and clear errors using PyMuPDF. No OCR.

## M3 — Learning Goals
**Status:** TODO

Create one active learning goal and associate 3–5 books.

## M4 — Book Profiles
**Status:** TODO

Difficulty, prerequisites, topics, strengths, weaknesses, theory/practice orientation, and editable profile.

## M5 — Book Comparison
**Status:** TODO

Compare overlap, prerequisites, difficulty, coverage, classify book role, and explain rationale.

## M6 — Learning Path
**Status:** TODO

Generate dependency-aware stages, selected chapters, skip/reference decisions, mastery evidence, and `STUDY_PLAN.md`.

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

## Active Task

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
Status: READY FOR TEST
Approval: User approved the Git Baseline Before M1 plan and its local commit on 2026-09-17.

Goal: establish one local baseline commit of exactly the approved 38 project files on main.
Scope: add the approved ignore patterns, initialize Git at the project root, stage the explicit manifest, inspect the staged diff, commit, and verify branch/file inventory/clean working tree/no remotes.
Acceptance: main branch; exactly 38 approved tracked files; local artifacts ignored and environment examples tracked; one reviewed baseline commit; clean working tree; no remote.
Files edited: .gitignore and TASKS.md only. Existing M0 source, tests, dependencies, documentation, and certification otherwise preserved.
Commit message: `chore: establish verified M0 baseline`.
No application recertification required by this approved maintenance plan. M0 stays DONE; M1 stays TODO. No remote, push, global identity change, dependency change, or application refactor.

Pre-commit verification: Git initialized on main; 23 ignore probes passed; all 38 approved files (including both .env.example files) remain trackable; unignored inventory exactly matches the manifest. Credential-pattern scan found no matches. Only .gitignore and TASKS.md were edited; no runtime files removed.
Final commit/tree/status verification is performed after creating the baseline and reported in the task response. This CODE record does not change M0 certification or mark a new product milestone DONE.
