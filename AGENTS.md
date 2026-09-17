# AGENTS.md — PDF Learning OS

## Required Reading Before Every Task

1. `AGENTS.md`
2. `PROJECT.md`
3. `SOFTWARE_REQUIREMENTS.md`
4. `ARCHITECTURE.md`
5. `LEARNING_MODEL.md`
6. `TASKS.md`
7. Relevant source/tests
8. Git status/diff

Do not implement from the latest chat message alone when repository context exists.

## MODE: PLAN

Use for new features, architecture decisions, schema changes, dependencies, ambiguous behavior, or scope changes.

PLAN must include:
- current-state finding
- goal
- files expected to change
- implementation steps
- acceptance criteria
- tests
- risks/edge cases
- out-of-scope items
- `TASKS.md` update

Do not implement production code or mark DONE.

## MODE: CODE

Before coding:
- confirm approved task in `TASKS.md`
- confirm acceptance criteria

During coding:
- implement only current task
- keep changes small
- avoid unrelated refactors
- preserve source integrity
- add/update relevant tests

After coding:
- update `TASKS.md`
- mark `READY FOR TEST`
- do not mark DONE

## MODE: TEST

Frontend quality gate:

```bash
npm run lint
npm run test -- --run
npm run build
```

If configured:

```bash
npm run typecheck
```

Backend:

```bash
pytest
```

Only after acceptance criteria and checks pass:
- mark DONE
- update `CHANGELOG.md`

## MODE: FULL

Only when explicitly requested. Execute one small task through `PLAN → CODE → TEST`. Never multiple milestones.

## Model Guidance

For architecture, difficult debugging, schema design, PDF parsing edge cases, and cross-cutting changes, prefer the strongest reasoning-capable Codex model available. If GPT-5.6 Sol is available, use Sol High for PLAN and difficult TEST/DEBUG. Use a faster coding-capable model for straightforward implementation.

## Documentation Rules

- Workflow rules → `AGENTS.md`
- Product scope → `PROJECT.md`
- Behavior/requirements → `SOFTWARE_REQUIREMENTS.md`
- Architecture → `ARCHITECTURE.md`
- Learning/mastery rules → `LEARNING_MODEL.md`
- Active work/status/tests → `TASKS.md`
- Verified completed work → `CHANGELOG.md`

## Scope Discipline

V0.1 must not add vector DB, embeddings, RAG, autonomous agents, multi-user auth, LMS, public SaaS, mobile app, cloud architecture, realtime collaboration, arbitrary code execution, or advanced spaced repetition without explicit approval.

## Source Integrity

Preserve original extracted text and page references. Never silently rewrite source text. Clearly label generated content. Do not invent missing book content.

## Definition of Done

DONE requires:
- acceptance criteria pass
- tests pass
- lint/build pass where relevant
- source integrity preserved
- no unapproved scope
- `TASKS.md` updated
- `CHANGELOG.md` updated
