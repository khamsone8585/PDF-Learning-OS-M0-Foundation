# CHANGELOG.md — PDF Learning OS

Only record completed and verified work.

## Unreleased

### M0 — Repository Foundation — 2026-09-17

- Added the React/TypeScript/Vite app shell with accessible local health states, timeout handling, and restricted local API configuration.
- Added FastAPI `GET /health` with SQLAlchemy 2.x/SQLite connectivity, safe failure responses, and local CORS restrictions; no domain tables.
- Added isolated backend tests, frontend health-state tests, dependency locks, local-data ignore rules, and development documentation.
- Verified lint, build, typecheck, 11 frontend tests and 13 backend tests (zero failures), live HTTP health/CORS checks, and real Safari ready/unavailable/recovery behavior.
- No PDF, AI, learning, or M1+ features included. Git status/diff unavailable because the workspace is not initialized as a Git repository.
