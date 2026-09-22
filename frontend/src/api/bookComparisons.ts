import { LibraryError, request } from './books'
import type { BookProfile, BookProfileInput } from './bookProfiles'

export const roleLabels = { core: 'CORE', selected_chapters: 'SELECTED CHAPTERS',
  reference: 'REFERENCE', skip_for_now: 'SKIP FOR NOW' } as const
export type Role = keyof typeof roleLabels
export interface Assessment<C extends string = string> { category: C; explanation: string }
export type Evidence = { kind: 'profile_field'; field: keyof BookProfileInput } |
  { kind: 'topic'; topic: string } |
  { kind: 'pair'; other_book_id: string; dimension: 'overlap' | 'difficulty' | 'prerequisites' }
export interface Judgment {
  book_id: string
  role: Role
  rationale: string
  relevance: Assessment<'high' | 'partial' | 'low' | 'unknown'>
  depth: Assessment<'overview' | 'working_detail' | 'deep_treatment'> | null
  practice: Assessment<'limited' | 'some' | 'substantial'> | null
  focus_topics: string[]
  evidence_refs: Evidence[]
  reviewed: boolean
}
export interface BookInput {
  book_id: string; title: string; profile: BookProfile
  topic_keys: string[]; topic_count: number; unique_topics: string[]
}
export interface SetComparison { shared: string[]; left_only: string[]; right_only: string[] }
export interface PairComparison {
  left_book_id: string; right_book_id: string; overlap: SetComparison
  difficulty: 'lower' | 'same' | 'higher' | 'unknown'
  prerequisites: SetComparison | null
}
export interface Preview {
  goal: { id: string; title: string; description: string | null; updated_at: string; book_ids: string[] }
  books: BookInput[]
  coverage: Array<{ topic: string; book_ids: string[] }>
  pairs: PairComparison[]
  algorithm_version: string
  derived_source: 'derived'
}
export interface Snapshot {
  preview: Preview
  books: Array<Judgment & { provenance: Record<string, 'manual' | null> }>
  revision: number; input_token: string; created_at: string; updated_at: string
}
export interface Comparison {
  goal_id: string; is_active: boolean
  readiness: { ready: boolean; issues: Array<{ code: string; message: string; book_id: string | null }> }
  input_token: string | null; current: Preview | null; saved: Snapshot | null
  stale: boolean; stale_reasons: string[]
}
export interface ComparisonInput {
  input_token: string; expected_revision: number | null; books: Judgment[]
}

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object'
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(v => typeof v === 'string')
const textOrNull = (value: unknown) => value === null || typeof value === 'string'
const assessment = (value: unknown, categories: string[]) => object(value) &&
  categories.includes(String(value.category)) && typeof value.explanation === 'string'
const setComparison = (value: unknown) => object(value) &&
  strings(value.shared) && strings(value.left_only) && strings(value.right_only)

function preview(value: unknown): value is Preview {
  if (!object(value) || !object(value.goal) || !strings(value.goal.book_ids) ||
      !['id', 'title', 'updated_at'].every(k => typeof (value.goal as Record<string, unknown>)[k] === 'string') ||
      !textOrNull(value.goal.description) || typeof value.algorithm_version !== 'string' ||
      value.derived_source !== 'derived') return false
  return Array.isArray(value.books) && value.books.every(book => {
    if (!object(book) || typeof book.book_id !== 'string' || typeof book.title !== 'string' ||
        !strings(book.topic_keys) || !strings(book.unique_topics) || !Number.isInteger(book.topic_count) ||
        !object(book.profile) || !object(book.profile.provenance)) return false
    const p = book.profile
    const provenance = p.provenance as Record<string, unknown>
    return ['book_id', 'created_at', 'updated_at'].every(k => typeof p[k] === 'string') &&
      ['domain', 'suggested_use'].every(k => textOrNull(p[k])) &&
      (p.difficulty === null || ['beginner', 'intermediate', 'advanced'].includes(String(p.difficulty))) &&
      (p.orientation === null || ['theory_heavy', 'balanced', 'practice_heavy'].includes(String(p.orientation))) &&
      ['main_topics', 'prerequisites', 'strengths', 'weaknesses'].every(k => strings(p[k])) &&
      ['domain', 'difficulty', 'main_topics', 'prerequisites', 'orientation', 'strengths', 'weaknesses', 'suggested_use']
        .every(k => provenance[k] === null || ['manual', 'derived', 'ai_generated', 'ai_assisted'].includes(String(provenance[k])))
  }) && Array.isArray(value.coverage) && value.coverage.every(c => object(c) &&
    typeof c.topic === 'string' && strings(c.book_ids)) &&
    Array.isArray(value.pairs) && value.pairs.every(p => object(p) &&
      typeof p.left_book_id === 'string' && typeof p.right_book_id === 'string' &&
      ['lower', 'same', 'higher', 'unknown'].includes(String(p.difficulty)) &&
      setComparison(p.overlap) && (p.prerequisites === null || setComparison(p.prerequisites)))
}

function judgment(value: unknown): boolean {
  if (!object(value)) return false
  return typeof value.book_id === 'string' && Object.hasOwn(roleLabels, String(value.role)) &&
    typeof value.rationale === 'string' && value.reviewed === true &&
    assessment(value.relevance, ['high', 'partial', 'low', 'unknown']) &&
    (value.depth === null || assessment(value.depth, ['overview', 'working_detail', 'deep_treatment'])) &&
    (value.practice === null || assessment(value.practice, ['limited', 'some', 'substantial'])) &&
    strings(value.focus_topics) && Array.isArray(value.evidence_refs) && value.evidence_refs.every(ref =>
      object(ref) && (ref.kind === 'profile_field' ? typeof ref.field === 'string'
        : ref.kind === 'topic' ? typeof ref.topic === 'string'
          : ref.kind === 'pair' && typeof ref.other_book_id === 'string' &&
            ['overlap', 'difficulty', 'prerequisites'].includes(String(ref.dimension)))) &&
    object(value.provenance) &&
    ['role', 'rationale', 'relevance', 'depth', 'practice', 'focus_topics', 'evidence_refs'].every(k =>
      (value.provenance as Record<string, unknown>)[k] === 'manual' || (value.provenance as Record<string, unknown>)[k] === null)
}

function comparison(value: unknown): value is Comparison {
  if (!object(value) || typeof value.goal_id !== 'string' || typeof value.is_active !== 'boolean' ||
      !object(value.readiness) || typeof value.readiness.ready !== 'boolean' ||
      !Array.isArray(value.readiness.issues) || !value.readiness.issues.every(i => object(i) &&
        typeof i.code === 'string' && typeof i.message === 'string' && textOrNull(i.book_id)) ||
      !textOrNull(value.input_token) || typeof value.stale !== 'boolean' || !strings(value.stale_reasons)) return false
  if (value.current !== null && !preview(value.current)) return false
  if (value.saved !== null) {
    const s = value.saved
    if (!object(s) || !preview(s.preview) || !Array.isArray(s.books) || !s.books.every(judgment) ||
        !Number.isInteger(s.revision) || Number(s.revision) < 1 ||
        !['input_token', 'created_at', 'updated_at'].every(k => typeof s[k] === 'string')) return false
  }
  return true
}

export async function getComparison(goalId: string, signal?: AbortSignal): Promise<Comparison> {
  const result = await request(`/learning-goals/${encodeURIComponent(goalId)}/comparison`, 'GET', signal)
  if (!comparison(result)) throw new LibraryError('Unexpected comparison response.')
  return result
}

export async function putComparison(goalId: string, value: ComparisonInput, signal?: AbortSignal): Promise<Comparison> {
  const result = await request(`/learning-goals/${encodeURIComponent(goalId)}/comparison`, 'PUT',
    signal, JSON.stringify(value), 120000, { 'Content-Type': 'application/json' })
  if (!comparison(result)) throw new LibraryError('The comparison save result is unknown. Reload before retrying.', 'outcome_unknown')
  return result
}

export function evidenceOptions(book: BookInput, current: Preview): Array<{ value: Evidence; label: string }> {
  const fields: Array<keyof BookProfileInput> = ['domain', 'difficulty', 'prerequisites', 'main_topics',
    'orientation', 'strengths', 'weaknesses', 'suggested_use']
  const result: Array<{ value: Evidence; label: string }> = fields.filter(field => {
    const value = book.profile[field]
    return Array.isArray(value) ? value.length > 0 : !!value
  }).map(field => ({ value: { kind: 'profile_field', field }, label: `Profile: ${field.replaceAll('_', ' ')}` }))
  for (const topic of book.topic_keys) result.push({ value: { kind: 'topic', topic }, label: `Topic: ${topic}` })
  for (const pair of current.pairs.filter(p => [p.left_book_id, p.right_book_id].includes(book.book_id))) {
    const other = pair.left_book_id === book.book_id ? pair.right_book_id : pair.left_book_id
    for (const dimension of ['overlap', 'difficulty', 'prerequisites'] as const) {
      if (pair[dimension] === null || pair[dimension] === 'unknown') continue
      result.push({ value: { kind: 'pair', other_book_id: other, dimension },
        label: `${dimension} with ${current.books.find(b => b.book_id === other)?.title || other}` })
    }
  }
  return result
}

export const evidenceKey = (value: Evidence) => value.kind === 'profile_field' ? `field:${value.field}`
  : value.kind === 'topic' ? `topic:${value.topic}` : `pair:${value.other_book_id}:${value.dimension}`
