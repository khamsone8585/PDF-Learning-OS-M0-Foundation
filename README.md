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

## M0 local development

M0 provides a connection-status screen and `GET /health`. Product features arrive in later milestones.

Tested toolchain: Node 22.20.0, npm 10.9.3, and Python 3.14.5. Supported runtime ranges are Node 22 (at least 22.12) and Python 3.14. Dependency locks are in `frontend/package-lock.json` and `backend/requirements.lock`. npm 10.9.3 successfully installs the frontend lock with `npm ci`. If regenerating that lock, use `npm exec --yes --package npm@11.16.0 -- npm install` to avoid an npm 10 peer-resolution crash; this does not replace your global npm.

### Backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The default database is `data/learning_os.sqlite3` under the repository root, independent of the server's working directory. Its directory is created as needed. To override it, set `PDF_LEARNING_DATA_DIR` in the shell before starting the server. Relative paths resolve against the repository root; `~` is expanded. `backend/.env.example` documents the variable; the backend does not automatically read `.env` files.

No domain tables or migrations are created. Health verifies connectivity using `SELECT 1`; it does not guarantee write readiness. If storage initialization fails, health reports unavailable; fix the directory and restart the backend.

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

Tests use temporary SQLite paths; they do not use the runtime library directory.

With both servers running:

```bash
curl -i http://127.0.0.1:8000/health
```

Expect HTTP 200 and `{"status":"ok","database":"ok"}`. Database failure returns HTTP 503 and `{"status":"error","database":"unavailable"}` without local paths or exception details.

The screen starts with “Checking local connection…” and then shows “Ready”. Stop the backend and reload: it should show “Unavailable”, with stalled requests timing out after five seconds. Restart the backend and reload to confirm recovery. Status is checked on mount, without polling. Confirm the database remains at the configured local path after restart.

Runtime databases, virtual environments, frontend dependencies/builds, and local environment files are ignored. No external service, API key, or PDF is needed to run M0 after dependency installation.
