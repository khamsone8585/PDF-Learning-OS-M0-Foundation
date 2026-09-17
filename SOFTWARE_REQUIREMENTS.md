# SOFTWARE_REQUIREMENTS.md — PDF Learning OS V0.1

## 1. Purpose

PDF Learning OS is a local-first personal learning application for studying technical books and PDFs deeply and systematically.

Primary loop:

`Library → Analyze → Prioritize → Study → Recall → Apply → Mastery → Review`

## 2. Primary User

V0.1 supports one learner studying technical subjects such as Computer Science, Software Engineering, Data Science, Machine Learning, and Research.

## 3. Functional Requirements

### Library
- **FR-001** Import a local PDF.
- **FR-002** Store title, filename, author/edition/year when available, page count, and import time.
- **FR-003** List imported books.
- **FR-004** Open book details.
- **FR-005** Remove a book and derived local data after confirmation.

### PDF Processing
- **FR-006** Extract machine-readable text from text PDFs.
- **FR-007** Extract PDF bookmarks/TOC when available.
- **FR-008** Preserve page references.
- **FR-009** Map chapters/sections from TOC when possible.
- **FR-010** Allow correction of fallback chapter structure.
- **FR-011** Show processing state and extraction errors.

OCR is out of scope for V0.1.

### Learning Goals
- **FR-012** Create an active learning goal.
- **FR-013** Associate 3–5 books with a learning goal.

### Book Profiles
- **FR-014** Store domain, difficulty, prerequisites, main topics, theory/practice orientation, strengths, weaknesses, and suggested use.
- **FR-015** Allow manual editing of profile fields.

### Book Comparison
- **FR-016** Compare books by topic coverage, difficulty, prerequisites, depth, practice content, overlap, and relevance.
- **FR-017** Classify each book as CORE, SELECTED CHAPTERS, REFERENCE, or SKIP FOR NOW.
- **FR-018** Explain every classification.

### Learning Path
- **FR-019** Recommend order based on dependencies/prerequisites.
- **FR-020** Support read / selected chapters / reference / skip decisions.
- **FR-021** Explain ordering rationale.
- **FR-022** Export `STUDY_PLAN.md`.

### Study Reader
- **FR-023** Open a chapter/section.
- **FR-024** Show original extracted source text.
- **FR-025** Preserve book/chapter/section/page context.
- **FR-026** Allow selecting a passage for study actions.

### Translation & Explanation
- **FR-027** Translate selected text into Thai or Lao while keeping technical English terms visible.
- **FR-028** Provide simplified English.
- **FR-029** Support Simple / Academic / Technical explanation levels.
- **FR-030** Clearly distinguish generated content from source text.

### Active Recall
- **FR-031** Support explain-back before ideal explanation.
- **FR-032** Evaluate correct ideas, missing concepts, and misconceptions.
- **FR-033** Generate source-grounded recall questions.
- **FR-034** Generate short quizzes.
- **FR-035** Reveal correct answer with rationale and source scope where applicable.

### Practice
- **FR-036** Provide suitable practice prompts such as coding, data analysis, algorithm tracing, debugging, or teach-back. V0.1 does not execute arbitrary code.

### Mastery
- **FR-037** Support mastery levels 0–5 from `LEARNING_MODEL.md`.
- **FR-038** Store evidence such as reading, explanation, recall, quiz, practice, or teach-back.
- **FR-039** Reading alone cannot grant advanced mastery.
- **FR-040** Allow manual mastery correction.

### Progress
- **FR-041** Show progress by learning goal, book, chapter, and concept when available.
- **FR-042** Support a Review Needed state.

### Markdown Artifacts
- **FR-043** Export `PROFILE.md`.
- **FR-044** Export `CHAPTER_NOTES.md`.
- **FR-045** Export `STUDY_PLAN.md`.
- **FR-046** Export `PROGRESS.md`.
- **FR-047** Export a teaching note when needed.

## 4. Non-Functional Requirements

- **NFR-001 Local First:** PDF library, extracted content, and progress remain local.
- **NFR-002 Privacy Boundary:** Source text is not sent to external AI unless an explicit AI action uses a configured provider.
- **NFR-003 Source Integrity:** Original extracted text is never silently rewritten.
- **NFR-004 Source Grounding:** Book-dependent AI actions use relevant source scope.
- **NFR-005 Persistence:** Data survives restarts.
- **NFR-006 Performance:** Already processed chapters should open quickly on a normal laptop.
- **NFR-007 Accessibility:** Core controls are keyboard-accessible.
- **NFR-008 Maintainability:** PDF, AI, learning-path, and mastery logic are separated.
- **NFR-009 Testability:** Core business rules are independently testable.
- **NFR-010 Provider Isolation:** AI provider is behind an adapter/interface.
- **NFR-011 No Premature Infrastructure:** No Redis, Celery, Kubernetes, vector DB, embeddings service, or cloud hosting required.
- **NFR-012 Recoverability:** Processing failures must not corrupt the library.

## 5. System Acceptance Criteria

V0.1 is acceptable when the learner can import 3 real technical PDFs, process metadata/text/TOC, define one learning goal, compare books, receive a justified order, export `STUDY_PLAN.md`, study a chapter, use translation/explanation, complete recall/quiz, record mastery evidence, export notes/progress, and complete a real 2–4 week pilot without RAG/vector infrastructure.
