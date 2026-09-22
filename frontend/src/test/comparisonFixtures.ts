import type { Comparison, ComparisonInput } from '../api/bookComparisons'
import type { LearningGoal } from '../api/learningGoals'

export const ids = [1, 2, 3].map(i => `00000000-0000-4000-8000-00000000000${i}`)
const timestamp = '2026-09-22T00:00:00Z'
export const comparisonGoal: LearningGoal = { id: '00000000-0000-4000-8000-000000000009',
  title: 'Study algorithms', description: 'For practical use', is_active: true,
  book_ids: ids, created_at: timestamp, updated_at: timestamp }

export function readyComparison(): Comparison {
  return { goal_id: comparisonGoal.id, is_active: true, readiness: { ready: true, issues: [] },
    input_token: 'a'.repeat(64), saved: null, stale: false, stale_reasons: [], current: {
      goal: { id: comparisonGoal.id, title: comparisonGoal.title, description: comparisonGoal.description,
        updated_at: timestamp, book_ids: ids }, algorithm_version: 'profile_exact_v1', derived_source: 'derived',
      books: ids.map((id, i) => ({ book_id: id, title: `Book ${i + 1}`, topic_keys: ['algorithms'],
        topic_count: 1, unique_topics: [], profile: { book_id: id, domain: 'Computing', difficulty: 'beginner',
          prerequisites: [], main_topics: ['Algorithms'], orientation: 'balanced', strengths: ['Examples'],
          weaknesses: [], suggested_use: null, created_at: timestamp, updated_at: timestamp,
          provenance: { domain: 'manual', difficulty: 'manual', prerequisites: null, main_topics: 'manual',
            orientation: 'manual', strengths: 'manual', weaknesses: null, suggested_use: null } } })),
      coverage: [{ topic: 'algorithms', book_ids: ids }], pairs: ids.flatMap((id, i) => ids.slice(i + 1).map(other => ({
        left_book_id: id, right_book_id: other, difficulty: 'same' as const, prerequisites: null,
        overlap: { shared: ['algorithms'], left_only: [], right_only: [] } }))),
    } }
}

export function comparisonRequest(): ComparisonInput {
  return { input_token: 'a'.repeat(64), expected_revision: null, books: ids.map(book_id => ({
    book_id, role: 'core', rationale: 'Primary resource', relevance: { category: 'high', explanation: 'Relevant topics' },
    depth: null, practice: null, focus_topics: [], evidence_refs: [], reviewed: true,
  })) }
}

export function savedComparison(): Comparison {
  const result = readyComparison()
  result.saved = { preview: result.current!, books: comparisonRequest().books.map(j => ({ ...j,
    provenance: { role: 'manual', rationale: 'manual', relevance: 'manual', depth: null,
      practice: null, focus_topics: null, evidence_refs: null } })), revision: 1,
    input_token: result.input_token!, created_at: timestamp, updated_at: timestamp }
  return result
}
