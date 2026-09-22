import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { getComparison, putComparison } from '../../api/bookComparisons'
import type { Comparison } from '../../api/bookComparisons'
import { LibraryError } from '../../api/books'
import { comparisonGoal, ids, readyComparison, savedComparison } from '../../test/comparisonFixtures'
import BookComparisonPanel from './BookComparisonPanel'

vi.mock('../../api/bookComparisons', async importOriginal => ({
  ...await importOriginal<typeof import('../../api/bookComparisons')>(), getComparison: vi.fn(), putComparison: vi.fn(),
}))
beforeEach(() => {
  vi.mocked(getComparison).mockReset().mockResolvedValue(readyComparison())
  vi.mocked(putComparison).mockReset().mockResolvedValue(savedComparison())
})
const panel = () => render(<BookComparisonPanel goal={comparisonGoal} disabled={false} />)
async function edit() { fireEvent.click(await screen.findByRole('button', { name: 'Classify books' })) }
function fill() {
  for (const fieldset of screen.getAllByRole('group', { name: /Book \d — manual judgments/ })) {
    const q = within(fieldset)
    fireEvent.change(q.getByLabelText('Role'), { target: { value: 'core' } })
    fireEvent.change(q.getByLabelText('Classification rationale'), { target: { value: 'My rationale' } })
    fireEvent.change(q.getByLabelText('Relevance explanation'), { target: { value: 'My relevance' } })
    fireEvent.click(q.getByLabelText(/I reviewed this book/))
  }
}

it('shows explicit readiness issues and opens a profile without comparative results', async () => {
  const data = readyComparison()
  data.current = null; data.input_token = null
  data.readiness = { ready: false, issues: [{ code: 'profile_missing', book_id: ids[0], message: 'Record a book profile.' }] }
  vi.mocked(getComparison).mockResolvedValue(data)
  const open = vi.fn()
  render(<BookComparisonPanel goal={comparisonGoal} disabled={false} onOpenBook={open} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Open profile for 1' }))
  expect(open).toHaveBeenCalledWith(ids[0])
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

it('renders facts with matching limitations and unknown prerequisites', async () => {
  panel()
  expect(await screen.findByRole('table', { name: 'Book comparison overview' })).toBeInTheDocument()
  expect(screen.getByText(/synonyms, acronyms and meaning/)).toBeInTheDocument()
  fireEvent.click(screen.getByText('Pairwise overlap, difficulty and prerequisites — derived'))
  expect(screen.getAllByText(/Prerequisite comparison unknown/)).toHaveLength(3)
  expect(screen.getByRole('button', { name: 'Classify books' })).toBeEnabled()
})

it('creates manual judgments and restores focus with success announcement', async () => {
  panel(); await edit(); fill()
  fireEvent.click(screen.getByRole('button', { name: 'Save comparison' }))
  await waitFor(() => expect(putComparison).toHaveBeenCalledTimes(1))
  const body = vi.mocked(putComparison).mock.calls[0][1]
  expect(body.books).toHaveLength(3)
  expect(body.books.every(b => b.reviewed && b.role === 'core')).toBe(true)
  expect(body.books[0]).not.toHaveProperty('provenance')
  expect(await screen.findByText('Comparison saved.')).toBeInTheDocument()
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Book comparison' })).toHaveFocus())
})

it('requires selected-chapters focus and explicit review after changes', async () => {
  panel(); await edit(); fill()
  const q = within(screen.getAllByRole('group', { name: /Book \d — manual judgments/ })[0])
  fireEvent.change(q.getByLabelText('Role'), { target: { value: 'selected_chapters' } })
  expect(q.getByLabelText(/I reviewed/)).not.toBeChecked()
  fireEvent.click(q.getByLabelText(/I reviewed/))
  fireEvent.click(screen.getByRole('button', { name: 'Save comparison' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(/focus topics|references/i)
  expect(putComparison).not.toHaveBeenCalled()
  fireEvent.click(q.getByLabelText('algorithms'))
  fireEvent.click(q.getByLabelText(/I reviewed/))
  fireEvent.click(screen.getByRole('button', { name: 'Save comparison' }))
  await waitFor(() => expect(putComparison).toHaveBeenCalledTimes(1))
})

it('supports optional manual depth/practice and cancel without saving', async () => {
  panel(); await edit()
  const q = within(screen.getAllByRole('group', { name: /Book \d — manual judgments/ })[0])
  fireEvent.change(q.getByLabelText('Depth'), { target: { value: 'deep_treatment' } })
  fireEvent.change(q.getByLabelText('Practice content'), { target: { value: 'substantial' } })
  expect(q.getByLabelText('Depth explanation')).toBeRequired()
  expect(q.getByLabelText('Practice content explanation')).toBeRequired()
  fireEvent.click(screen.getByRole('button', { name: 'Cancel comparison edit' }))
  expect(screen.queryByLabelText('Depth explanation')).not.toBeInTheDocument()
  expect(putComparison).not.toHaveBeenCalled()
})

it('preserves drafts on server errors and does not replay ambiguous saves', async () => {
  vi.mocked(putComparison).mockRejectedValue(new LibraryError('Unknown result', 'outcome_unknown'))
  panel(); await edit(); fill()
  fireEvent.click(screen.getByRole('button', { name: 'Save comparison' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Unknown result')
  await waitFor(() => expect(getComparison).toHaveBeenCalledTimes(2))
  expect(screen.getAllByLabelText('Classification rationale')[0]).toHaveValue('My rationale')
  expect(putComparison).toHaveBeenCalledTimes(1)
})

it('refreshes stale inputs, carries judgments by ID and flags invalid references', async () => {
  const original = savedComparison()
  original.saved!.books[0].focus_topics = ['removed']
  original.saved!.books[0].evidence_refs = [{ kind: 'topic', topic: 'removed' }]
  original.stale = true; original.stale_reasons = ['inputs_changed']; original.input_token = 'b'.repeat(64)
  vi.mocked(getComparison).mockResolvedValue(original)
  panel()
  fireEvent.click(await screen.findByRole('button', { name: 'Review with current inputs' }))
  expect(screen.getAllByLabelText('Classification rationale')[0]).toHaveValue('Primary resource')
  expect(screen.getAllByLabelText(/I reviewed/).every(e => !(e as HTMLInputElement).checked)).toBe(true)
  expect(screen.getByText('removed — unavailable; remove')).toBeInTheDocument()
  expect(screen.getByText(/Unavailable evidence — remove/)).toBeInTheDocument()
})

it('detects changed inputs on focus and requires review without discarding draft', async () => {
  panel(); await edit(); fill()
  vi.mocked(getComparison).mockResolvedValue({ ...readyComparison(), input_token: 'b'.repeat(64) })
  fireEvent(window, new Event('focus'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Your draft is preserved')
  expect(screen.getByRole('button', { name: 'Save comparison' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Review with current inputs' }))
  expect(screen.getAllByLabelText('Classification rationale')[0]).toHaveValue('My rationale')
  expect(screen.getAllByLabelText(/I reviewed/)[0]).not.toBeChecked()
})

it('disables editing while a mutation is in flight', async () => {
  let resolve!: (value: Comparison) => void
  vi.mocked(putComparison).mockReturnValue(new Promise(done => { resolve = done }))
  panel(); await edit(); fill()
  fireEvent.click(screen.getByRole('button', { name: 'Save comparison' }))
  expect(screen.getByRole('button', { name: 'Saving comparison…' })).toBeDisabled()
  expect(screen.getAllByLabelText('Role')[0]).toBeDisabled()
  await act(async () => resolve(savedComparison()))
})

it('can retry a read failure using explicit refresh', async () => {
  vi.mocked(getComparison).mockRejectedValueOnce(new LibraryError('Storage unavailable'))
  panel()
  expect(await screen.findByRole('alert')).toHaveTextContent('Storage unavailable')
  fireEvent.click(screen.getByRole('button', { name: 'Refresh comparison' }))
  expect(await screen.findByRole('button', { name: 'Classify books' })).toBeInTheDocument()
})

it('refreshes after profile and goal-selection signals without overwriting the editor', async () => {
  const view = panel(); await edit(); fill()
  vi.mocked(getComparison).mockResolvedValue({ ...readyComparison(), input_token: 'c'.repeat(64) })
  view.rerender(<BookComparisonPanel goal={comparisonGoal} disabled={false} refreshKey={1} />)
  await waitFor(() => expect(getComparison).toHaveBeenCalledTimes(2))
  expect(await screen.findByRole('alert')).toHaveTextContent('Your draft is preserved')
  expect(screen.getAllByLabelText('Classification rationale')[0]).toHaveValue('My rationale')
  view.rerender(<BookComparisonPanel goal={{ ...comparisonGoal, updated_at: '2026-09-23T00:00:00Z' }}
    disabled={false} refreshKey={1} />)
  await waitFor(() => expect(getComparison).toHaveBeenCalledTimes(3))
})

it('retains draft after an ambiguous committed save and detects authoritative revision', async () => {
  panel(); await edit(); fill()
  vi.mocked(putComparison).mockRejectedValue(new LibraryError('Storage error', 'library_storage_unavailable'))
  vi.mocked(getComparison).mockResolvedValue(savedComparison())
  fireEvent.click(screen.getByRole('button', { name: 'Save comparison' }))
  expect(await screen.findByText(/Your draft is preserved/)).toBeInTheDocument()
  expect(screen.getAllByLabelText('Classification rationale')[0]).toHaveValue('My rationale')
  expect(screen.getByRole('button', { name: 'Save comparison' })).toBeDisabled()
  expect(putComparison).toHaveBeenCalledTimes(1)
})
