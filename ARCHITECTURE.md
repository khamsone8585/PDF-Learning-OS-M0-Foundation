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
