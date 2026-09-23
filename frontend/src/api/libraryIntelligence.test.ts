import { afterEach, expect, it, vi } from 'vitest'
import { confirmTriage, createTriage, getLibraryMap, getPrerequisites, getRelations,
  listTriages, putRelationReview, updateTriage } from './libraryIntelligence'

const map = { library_token: 'a'.repeat(64), exact_content_duplicates_prevented: true,
  counts: { books: 1 }, groups: { domains: [], topics: [], readiness: [] }, books: [{
    book_id: 'book', title: 'Book', author: null, edition: null, year: null,
    processing_status: 'unprocessed', toc_status: null, profile: null,
    readiness: 'profile_missing', domain_key: null, topic_keys: [], prerequisite_keys: [],
    unique_topics: [], bibliographic_relation_count: 0, topic_relation_count: 0,
    unique_topic_count: 0, prerequisite_count: 0,
  }] }
const session = { id: 'triage', title: 'Systems', description: null, target_topics: ['Systems'],
  target_domain: null, difficulty_ceiling: null, scope_kind: 'library_snapshot', book_ids: ['book'],
  revision: 1, algorithm_version: 'curriculum_triage_v1', status: 'draft', applied_goal_id: null,
  created_at: 'now', updated_at: 'now', applied_at: null }
const triage = { session, candidates: map.books, readiness: { ready_count: 0, candidate_count: 1,
  prerequisite_count: 0, issues: [] }, recommendation: { suggested_book_ids: [], partial: true,
  issues: [], covered_target_topics: [], uncovered_target_topics: ['systems'], books: [],
  algorithm_version: 'curriculum_triage_v1', ordering_has_study_sequence_meaning: false },
  input_token: 'b'.repeat(64), stale: false, stale_reasons: [] }
const fields = { title: 'Systems', description: null, target_topics: ['Systems'], target_domain: null,
  difficulty_ceiling: null, scope: { kind: 'library_snapshot' as const, book_ids: [] } }

afterEach(() => vi.unstubAllGlobals())

it('validates intelligence reads and sends strict review data', async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(map), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 0, offset: 0, limit: 25, items: [] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 0, offset: 0, limit: 25, items: [] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ left_book_id: 'a', right_book_id: 'b',
      decision: 'distinct', preferred_book_id: null, note: null, source: 'manual',
      created_at: 'now', updated_at: 'now' }), { status: 200 }))
  vi.stubGlobal('fetch', fetch)
  expect((await getLibraryMap()).counts.books).toBe(1)
  expect((await getRelations('bibliographic')).items).toEqual([])
  expect((await getPrerequisites()).items).toEqual([])
  await putRelationReview({ left_book_id: 'a', right_book_id: 'b', decision: 'distinct',
    preferred_book_id: null, note: null })
  expect(JSON.parse(fetch.mock.calls[3][1].body)).toMatchObject({ decision: 'distinct', preferred_book_id: null })
})

it('creates, updates, lists, and confirms triage without mutation replay fields', async () => {
  const confirmed = { triage: session, goal: { id: 'goal' }, comparison: {} }
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(triage), { status: 201 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(triage), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ triages: [session] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(confirmed), { status: 201 }))
  vi.stubGlobal('fetch', fetch)
  await createTriage(fields)
  await updateTriage('triage', { ...fields, input_token: 'b'.repeat(64), expected_revision: 1 })
  expect((await listTriages())[0].id).toBe('triage')
  await confirmTriage('triage', { input_token: 'b'.repeat(64), expected_revision: 1,
    reviewed_recommendation: true, books: [] })
  expect(JSON.parse(fetch.mock.calls[3][1].body)).toEqual({ input_token: 'b'.repeat(64),
    expected_revision: 1, reviewed_recommendation: true, books: [] })
})

it('rejects malformed map and triage responses', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 })))
  await expect(getLibraryMap()).rejects.toThrow('Unexpected library intelligence response')
  await expect(createTriage(fields)).rejects.toMatchObject({ code: 'outcome_unknown' })
})
