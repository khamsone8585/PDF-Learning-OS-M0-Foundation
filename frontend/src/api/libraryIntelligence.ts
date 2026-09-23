import { LibraryError, request } from './books'
import type { Judgment } from './bookComparisons'
import type { BookProfile, Difficulty, Orientation } from './bookProfiles'

export type Readiness = 'profile_missing' | 'topics_missing' | 'triage_ready'
export interface CandidateBook {
  book_id: string; title: string; author: string | null; edition: string | null; year: number | null
  processing_status: string; toc_status: string | null; profile: BookProfile | null
  readiness: Readiness; domain_key: string | null; topic_keys: string[]; prerequisite_keys: string[]
  unique_topics: string[]
}
export interface MapBook extends CandidateBook {
  bibliographic_relation_count: number; topic_relation_count: number
  unique_topic_count: number; prerequisite_count: number
}
export interface LibraryMap {
  library_token: string; exact_content_duplicates_prevented: boolean
  counts: Record<string, number>; groups: Record<string, Array<{ key: string; label: string; count: number }>>
  books: MapBook[]
}
export interface RelationReview {
  decision: 'same_work' | 'related_edition' | 'distinct'; preferred_book_id: string | null
  note: string | null; source: 'manual'; updated_at: string
}
export interface Relation {
  left_book_id: string; right_book_id: string; classification: string; algorithm_version: string
  evidence?: string[]; shared_topics?: string[]; left_only?: string[]; right_only?: string[]
  complementary?: boolean; review?: RelationReview | null
}
export interface Prerequisite {
  book_id: string; prerequisite: string; normalized_key: string; profile_source: string
  providers: Array<{ book_id: string; field: string; source: 'derived' }>
  unresolved: boolean; algorithm_version: string
}
export interface TriageSession {
  id: string; title: string; description: string | null; target_topics: string[]
  target_domain: string | null; difficulty_ceiling: Difficulty | null
  scope_kind: 'library_snapshot' | 'selected'; book_ids: string[]; revision: number
  algorithm_version: string; status: 'draft' | 'applied' | 'archived' | 'invalidated'
  applied_goal_id: string | null; created_at: string; updated_at: string; applied_at: string | null
}
export interface RecommendationBook {
  book_id: string; title: string
  band: 'direct' | 'foundation' | 'supporting' | 'no_recorded_match' | 'insufficient_data'
  matched_target_topics: string[]; matched_prerequisites: string[]; unique_topics: string[]
  difficulty: Difficulty | null; orientation: Orientation | null; above_ceiling: boolean
  preferred_same_work_book_id: string | null; source: 'derived'; algorithm_version: string
}
export interface TriageEnvelope {
  session: TriageSession; candidates: CandidateBook[]
  readiness: { ready_count: number; candidate_count: number; prerequisite_count: number;
    issues: Array<{ code: string; book_id: string; message: string }> }
  recommendation: { suggested_book_ids: string[]; partial: boolean; issues: Array<Record<string, unknown>>;
    covered_target_topics: string[]; uncovered_target_topics: string[]; books: RecommendationBook[];
    algorithm_version: string; ordering_has_study_sequence_meaning: false }
  input_token: string; stale: boolean; stale_reasons: string[]
}
export interface TriageFields {
  title: string; description: string | null; target_topics: string[]; target_domain: string | null
  difficulty_ceiling: Difficulty | null
  scope: { kind: 'library_snapshot' | 'selected'; book_ids: string[] }
}

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object'
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === 'string')
const textOrNull = (value: unknown) => value === null || typeof value === 'string'

function isCandidate(value: unknown, mapCounts = false): value is CandidateBook {
  if (!object(value) || typeof value.book_id !== 'string' || typeof value.title !== 'string' ||
      !textOrNull(value.author) || !textOrNull(value.edition) ||
      !(value.year === null || Number.isInteger(value.year)) || !textOrNull(value.toc_status) ||
      !['unprocessed', 'processing', 'processed', 'failed'].includes(String(value.processing_status)) ||
      !['profile_missing', 'topics_missing', 'triage_ready'].includes(String(value.readiness)) ||
      !textOrNull(value.domain_key) || !strings(value.topic_keys) || !strings(value.prerequisite_keys) ||
      !strings(value.unique_topics) || !(value.profile === null || object(value.profile))) return false
  return !mapCounts || ['bibliographic_relation_count', 'topic_relation_count', 'unique_topic_count',
    'prerequisite_count'].every(key => Number.isInteger(value[key]) && Number(value[key]) >= 0)
}

function isSession(value: unknown): value is TriageSession {
  return object(value) && ['id', 'title', 'algorithm_version', 'created_at', 'updated_at']
    .every(key => typeof value[key] === 'string') && textOrNull(value.description) &&
    strings(value.target_topics) && textOrNull(value.target_domain) && textOrNull(value.difficulty_ceiling) &&
    ['library_snapshot', 'selected'].includes(String(value.scope_kind)) && strings(value.book_ids) &&
    Number.isInteger(value.revision) && Number(value.revision) >= 1 &&
    ['draft', 'applied', 'archived', 'invalidated'].includes(String(value.status)) &&
    textOrNull(value.applied_goal_id) && textOrNull(value.applied_at)
}

function isMap(value: unknown): value is LibraryMap {
  return object(value) && typeof value.library_token === 'string' && object(value.counts) && object(value.groups) &&
    Array.isArray(value.books) && value.books.every(book => isCandidate(book, true))
}
function isPage(value: unknown): value is { total: number; items: unknown[] } {
  return object(value) && Number.isInteger(value.total) && Number(value.total) >= 0 &&
    Number.isInteger(value.offset) && Number.isInteger(value.limit) && Array.isArray(value.items)
}
function isTriage(value: unknown): value is TriageEnvelope {
  return object(value) && isSession(value.session) && Array.isArray(value.candidates) &&
    value.candidates.every(candidate => isCandidate(candidate)) && object(value.readiness) &&
    object(value.recommendation) && strings(value.recommendation.suggested_book_ids) &&
    typeof value.input_token === 'string' && typeof value.stale === 'boolean' && strings(value.stale_reasons)
}

export async function getLibraryMap(signal?: AbortSignal): Promise<LibraryMap> {
  const result = await request('/library-intelligence/map', 'GET', signal)
  if (!isMap(result)) throw new LibraryError('Unexpected library intelligence response.')
  return result
}
export async function getRelations(kind: 'bibliographic' | 'topic_overlap', signal?: AbortSignal,
                                   offset = 0, limit = 25, bookId?: string) {
  const book = bookId ? `&book_id=${encodeURIComponent(bookId)}` : ''
  const result = await request(`/library-intelligence/relations?kind=${kind}&offset=${offset}&limit=${limit}${book}`, 'GET', signal)
  if (!isPage(result) || !result.items.every(item => object(item) &&
      typeof item.left_book_id === 'string' && typeof item.right_book_id === 'string' &&
      typeof item.classification === 'string' && typeof item.algorithm_version === 'string')) {
    throw new LibraryError('Unexpected library relation response.')
  }
  return result as { total: number; offset: number; limit: number; items: Relation[] }
}
export async function getPrerequisites(signal?: AbortSignal, offset = 0, limit = 25, bookId?: string) {
  const book = bookId ? `&book_id=${encodeURIComponent(bookId)}` : ''
  const result = await request(`/library-intelligence/prerequisites?offset=${offset}&limit=${limit}${book}`, 'GET', signal)
  if (!isPage(result) || !result.items.every(item => object(item) && typeof item.book_id === 'string' &&
      typeof item.prerequisite === 'string' && typeof item.normalized_key === 'string' &&
      Array.isArray(item.providers) && typeof item.unresolved === 'boolean')) {
    throw new LibraryError('Unexpected prerequisite response.')
  }
  return result as { total: number; offset: number; limit: number; items: Prerequisite[] }
}
export async function putRelationReview(value: { left_book_id: string; right_book_id: string;
  decision: RelationReview['decision']; preferred_book_id: string | null; note: string | null }, signal?: AbortSignal) {
  const result = await request('/library-intelligence/relation-reviews', 'PUT', signal, JSON.stringify(value), 120000,
    { 'Content-Type': 'application/json' })
  if (!object(result) || !['same_work', 'related_edition', 'distinct'].includes(String(result.decision)) ||
      !textOrNull(result.preferred_book_id) || !textOrNull(result.note) || result.source !== 'manual' ||
      typeof result.updated_at !== 'string') {
    throw new LibraryError('The relation-review result is unknown. Reload before retrying.', 'outcome_unknown')
  }
  return result as unknown as RelationReview
}
export async function listTriages(signal?: AbortSignal): Promise<TriageSession[]> {
  const result = await request('/curriculum-triages', 'GET', signal)
  if (!object(result) || !Array.isArray(result.triages) || !result.triages.every(isSession)) {
    throw new LibraryError('Unexpected triage history response.')
  }
  return result.triages as TriageSession[]
}
export async function getTriage(id: string, signal?: AbortSignal): Promise<TriageEnvelope> {
  const result = await request(`/curriculum-triages/${encodeURIComponent(id)}`, 'GET', signal)
  if (!isTriage(result)) throw new LibraryError('Unexpected curriculum triage response.')
  return result
}
export async function createTriage(value: TriageFields & { archive_draft_id?: string | null }, signal?: AbortSignal) {
  const result = await request('/curriculum-triages', 'POST', signal, JSON.stringify(value), 120000,
    { 'Content-Type': 'application/json' })
  if (!isTriage(result)) throw new LibraryError('The triage result is unknown. Reload before retrying.', 'outcome_unknown')
  return result
}
export async function updateTriage(id: string, value: TriageFields & { input_token: string; expected_revision: number },
                                    signal?: AbortSignal) {
  const result = await request(`/curriculum-triages/${encodeURIComponent(id)}`, 'PUT', signal,
    JSON.stringify(value), 120000, { 'Content-Type': 'application/json' })
  if (!isTriage(result)) throw new LibraryError('The triage result is unknown. Reload before retrying.', 'outcome_unknown')
  return result
}
export async function confirmTriage(id: string, value: { input_token: string; expected_revision: number;
  reviewed_recommendation: true; books: Judgment[] }, signal?: AbortSignal) {
  const result = await request(`/curriculum-triages/${encodeURIComponent(id)}/confirm`, 'POST', signal,
    JSON.stringify(value), 120000, { 'Content-Type': 'application/json' })
  if (!object(result) || !object(result.goal) || typeof result.goal.id !== 'string') {
    throw new LibraryError('The confirmation result is unknown. Reload before retrying.', 'outcome_unknown')
  }
  return result
}
