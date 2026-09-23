import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import type { Book } from '../../api/books'
import type { LibraryMap, TriageEnvelope, TriageSession } from '../../api/libraryIntelligence'
import { confirmTriage, createTriage, getLibraryMap, getPrerequisites, getRelations,
  getTriage, listTriages, putRelationReview, updateTriage } from '../../api/libraryIntelligence'
import LibraryIntelligence from './LibraryIntelligence'

vi.mock('../../api/libraryIntelligence', () => ({
  getLibraryMap: vi.fn(), getRelations: vi.fn(), getPrerequisites: vi.fn(), listTriages: vi.fn(),
  getTriage: vi.fn(), createTriage: vi.fn(), updateTriage: vi.fn(), confirmTriage: vi.fn(),
  putRelationReview: vi.fn(),
}))

const ids = ['00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000002',
  '00000000-0000-4000-8000-000000000003']
const books: Book[] = ids.map((id, index) => ({ id, title: `Book ${index + 1}`,
  original_filename: `book-${index}.pdf`, author: 'Author', edition: null, year: null,
  page_count: 10, imported_at: 'now', size_bytes: 100, file_available: true,
  processing_status: 'unprocessed', processing_error: null, processing_started_at: null,
  processed_at: null, has_processed_content: false, toc_status: null }))
const profile = (book_id: string) => ({ book_id, domain: 'Systems', difficulty: 'intermediate' as const,
  prerequisites: [], main_topics: ['Systems'], orientation: 'balanced' as const,
  strengths: [], weaknesses: [], suggested_use: null, provenance: { domain: 'manual' as const,
    difficulty: 'manual' as const, prerequisites: null, main_topics: 'manual' as const,
    orientation: 'manual' as const, strengths: null, weaknesses: null, suggested_use: null },
  created_at: 'now', updated_at: 'now' })
const libraryMap: LibraryMap = { library_token: 'a'.repeat(64), exact_content_duplicates_prevented: true,
  counts: { books: 3, triage_ready: 3, profile_missing: 0, topics_missing: 0 },
  groups: { domains: [], topics: [], readiness: [] }, books: ids.map((book_id, index) => ({
    book_id, title: `Book ${index + 1}`, author: 'Author', edition: null, year: null,
    processing_status: 'unprocessed', toc_status: null, profile: profile(book_id), readiness: 'triage_ready',
    domain_key: 'systems', topic_keys: ['systems'], prerequisite_keys: [], unique_topics: [],
    bibliographic_relation_count: 0, topic_relation_count: 0, unique_topic_count: 0,
    prerequisite_count: 0,
  })) }
const session: TriageSession = { id: '10000000-0000-4000-8000-000000000001', title: 'Systems',
  description: null, target_topics: ['Systems'], target_domain: 'Systems', difficulty_ceiling: 'intermediate',
  scope_kind: 'library_snapshot', book_ids: ids, revision: 1, algorithm_version: 'curriculum_triage_v1',
  status: 'draft', applied_goal_id: null, created_at: 'now', updated_at: 'now', applied_at: null }
const envelope: TriageEnvelope = { session, candidates: libraryMap.books,
  readiness: { ready_count: 3, candidate_count: 3, prerequisite_count: 0, issues: [] },
  recommendation: { suggested_book_ids: ids, partial: false, issues: [],
    covered_target_topics: ['systems'], uncovered_target_topics: [], books: ids.map((book_id, index) => ({
      book_id, title: `Book ${index + 1}`, band: 'direct', matched_target_topics: ['systems'],
      matched_prerequisites: [], unique_topics: [], difficulty: 'intermediate', orientation: 'balanced',
      above_ceiling: false, preferred_same_work_book_id: null, source: 'derived',
      algorithm_version: 'curriculum_triage_v1',
    })), algorithm_version: 'curriculum_triage_v1', ordering_has_study_sequence_meaning: false },
  input_token: 'b'.repeat(64), stale: false, stale_reasons: [] }

beforeEach(() => {
  vi.mocked(getLibraryMap).mockReset().mockResolvedValue(libraryMap)
  vi.mocked(getRelations).mockReset().mockResolvedValue({ total: 0, offset: 0, limit: 25, items: [] })
  vi.mocked(getPrerequisites).mockReset().mockResolvedValue({ total: 0, offset: 0, limit: 25, items: [] })
  vi.mocked(listTriages).mockReset().mockResolvedValue([])
  vi.mocked(getTriage).mockReset().mockResolvedValue(envelope)
  vi.mocked(createTriage).mockReset().mockResolvedValue(envelope)
  vi.mocked(updateTriage).mockReset().mockResolvedValue(envelope)
  vi.mocked(confirmTriage).mockReset().mockResolvedValue({ goal: { id: 'goal' } })
  vi.mocked(putRelationReview).mockReset().mockResolvedValue({ decision: 'distinct', preferred_book_id: null,
    note: null, source: 'manual', updated_at: 'now' })
})

const renderPanel = (openBook = vi.fn(), applied = vi.fn()) => {
  render(<LibraryIntelligence books={books} disabled={false} onOpenBook={openBook}
    onBusyChange={vi.fn()} onApplied={applied} />)
  fireEvent.click(screen.getByRole('button', { name: 'Open library intelligence' }))
  return { openBook, applied }
}

it('renders a searchable grouped map and opens the existing profile workflow', async () => {
  const { openBook } = renderPanel()
  expect(await screen.findByText(/3 books · 3 triage ready/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Search books'), { target: { value: 'Book 2' } })
  expect(screen.queryByRole('button', { name: 'Book 1' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Book 2' }))
  expect(openBook).toHaveBeenCalledWith(ids[1])
  expect(screen.getByText(/No exact normalized title-and-author candidates/)).toBeInTheDocument()
})

it('filters a compact 100-book map without rendering pairwise tables', async () => {
  const largeBooks = Array.from({ length: 100 }, (_, index) => ({
    ...libraryMap.books[0], book_id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
    title: `Synthetic ${String(index + 1).padStart(3, '0')}`,
  }))
  vi.mocked(getLibraryMap).mockResolvedValue({ ...libraryMap, counts: { ...libraryMap.counts,
    books: 100, triage_ready: 100 }, books: largeBooks })
  renderPanel()
  expect(await screen.findByText(/100 books · 100 triage ready/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Search books'), { target: { value: 'Synthetic 100' } })
  expect(screen.getByRole('button', { name: 'Synthetic 100' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Synthetic 001' })).not.toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

it('creates a whole-library triage with structured intent', async () => {
  vi.mocked(listTriages).mockResolvedValueOnce([]).mockResolvedValue([session])
  renderPanel()
  await screen.findByText(/3 books · 3 triage ready/)
  fireEvent.change(screen.getByLabelText('Learning intent title'), { target: { value: 'Systems' } })
  fireEvent.change(screen.getByLabelText('Target topics (one per line)'), { target: { value: 'Systems' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create triage' }))
  await waitFor(() => expect(createTriage).toHaveBeenCalledWith(expect.objectContaining({
    title: 'Systems', target_topics: ['Systems'], scope: { kind: 'library_snapshot', book_ids: [] },
  }), expect.any(AbortSignal)))
  expect(await screen.findByText('Curriculum triage created.')).toBeInTheDocument()
})

it('requires complete manual review and confirms a three-book handoff', async () => {
  vi.mocked(listTriages).mockResolvedValue([session])
  const { applied } = renderPanel()
  await screen.findByRole('group', { name: /Confirm 3–5 Books Now/ })
  expect(screen.getByText(/Unselected candidates are LATER/)).toBeInTheDocument()
  const group = screen.getByRole('group', { name: /Confirm 3–5 Books Now/ })
  fireEvent.submit(within(group).getByRole('button', { name: 'Confirm Books Now' }).closest('form')!)
  expect(screen.getByRole('alert')).toHaveTextContent('reviewed the recommendation')
  for (const title of ['Book 1', 'Book 2', 'Book 3']) {
    const fieldset = screen.getByRole('group', { name: `${title} manual decision` })
    fireEvent.change(within(fieldset).getByLabelText('Role'), { target: { value: title === 'Book 1' ? 'core' : 'selected_chapters' } })
    fireEvent.change(within(fieldset).getByLabelText('Rationale'), { target: { value: 'Use now' } })
    fireEvent.change(within(fieldset).getByLabelText('Relevance explanation'), { target: { value: 'Exact topic' } })
    if (title !== 'Book 1') fireEvent.click(within(fieldset).getAllByRole('checkbox', { name: 'systems' })[0])
    fireEvent.click(within(fieldset).getByRole('checkbox', { name: /I reviewed this book/ }))
  }
  fireEvent.click(within(group).getByRole('checkbox', { name: /I reviewed the deterministic recommendation/ }))
  fireEvent.click(within(group).getByRole('button', { name: 'Confirm Books Now' }))
  await waitFor(() => expect(confirmTriage).toHaveBeenCalled())
  expect(applied).toHaveBeenCalled()
})

it('shows stale state and disables confirmation until synchronization', async () => {
  vi.mocked(listTriages).mockResolvedValue([session])
  vi.mocked(getTriage).mockResolvedValue({ ...envelope, stale: true, stale_reasons: ['inputs_changed'] })
  renderPanel()
  expect(await screen.findByRole('alert')).toHaveTextContent('inputs_changed')
  expect(screen.getByRole('group', { name: /Confirm 3–5 Books Now/ })).toBeDisabled()
})
