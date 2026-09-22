import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getBookProfile, putBookProfile } from '../../api/bookProfiles'
import type { BookProfile } from '../../api/bookProfiles'
import { LibraryError } from '../../api/books'
import type { Book } from '../../api/books'
import BookProfilePanel from './BookProfilePanel'

vi.mock('../../api/bookProfiles', () => ({ getBookProfile: vi.fn(), putBookProfile: vi.fn() }))

const book: Book = { id: '00000000-0000-4000-8000-000000000001', title: 'Algorithms',
  original_filename: 'algorithms.pdf', author: null, edition: null, year: null,
  page_count: 10, imported_at: '2026-09-22T00:00:00Z', size_bytes: 100, file_available: true,
  processing_status: 'unprocessed', processing_error: null, processing_started_at: null,
  processed_at: null, has_processed_content: false, toc_status: null }
const profile: BookProfile = { book_id: book.id, domain: 'Computer science',
  difficulty: 'intermediate', prerequisites: ['Programming'], main_topics: ['Algorithms'],
  orientation: 'balanced', strengths: ['Clear examples'], weaknesses: [],
  suggested_use: 'Primary introduction', provenance: { domain: 'manual', difficulty: 'manual',
    prerequisites: 'manual', main_topics: 'manual', orientation: 'manual', strengths: 'manual',
    weaknesses: null, suggested_use: 'manual' }, created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z' }

beforeEach(() => {
  vi.mocked(getBookProfile).mockReset().mockResolvedValue(null)
  vi.mocked(putBookProfile).mockReset().mockResolvedValue(profile)
})

describe('book profile panel', () => {
  it('shows the absent state and validates an empty profile', async () => {
    render(<BookProfilePanel book={book} disabled={false} onBusyChange={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Create profile' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter at least one profile field')
    expect(putBookProfile).not.toHaveBeenCalled()
  })

  it('creates a structured manual profile and restores focus', async () => {
    render(<BookProfilePanel book={book} disabled={false} onBusyChange={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Create profile' }))
    fireEvent.change(screen.getByLabelText('Domain'), { target: { value: 'Computer science' } })
    fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'intermediate' } })
    fireEvent.change(screen.getByLabelText(/Prerequisites/), { target: { value: 'Programming' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(await screen.findByText('Book profile saved.')).toBeInTheDocument()
    expect(putBookProfile).toHaveBeenCalledWith(book.id, expect.objectContaining({
      domain: 'Computer science', difficulty: 'intermediate', prerequisites: ['Programming'] }),
    expect.any(AbortSignal))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Book profile' })).toHaveFocus())
  })

  it('renders provenance and supports edit cancellation', async () => {
    vi.mocked(getBookProfile).mockResolvedValue(profile)
    render(<BookProfilePanel book={book} disabled={false} onBusyChange={vi.fn()} />)
    expect(await screen.findByText('Computer science')).toBeInTheDocument()
    expect(screen.getAllByText(/Manually entered/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Edit profile' }))
    fireEvent.change(screen.getByLabelText('Domain'), { target: { value: 'Changed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel profile edit' }))
    expect(screen.getByText('Computer science')).toBeInTheDocument()
    expect(putBookProfile).not.toHaveBeenCalled()
  })

  it('validates duplicate list values and preserves form after server errors', async () => {
    vi.mocked(putBookProfile).mockRejectedValue(new LibraryError('Save failed'))
    render(<BookProfilePanel book={book} disabled={false} onBusyChange={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Create profile' }))
    fireEvent.change(screen.getByLabelText(/Main topics/), { target: { value: 'Algorithms\nalgorithms' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(screen.getByRole('alert')).toHaveTextContent('must not contain duplicates')
    fireEvent.change(screen.getByLabelText(/Main topics/), { target: { value: 'Algorithms' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(await screen.findByText('Save failed')).toBeInTheDocument()
    expect(screen.getByLabelText(/Main topics/)).toHaveValue('Algorithms')
  })

  it('disables mutations while saving', async () => {
    let resolve!: (value: BookProfile) => void
    vi.mocked(putBookProfile).mockImplementation(() => new Promise(done => { resolve = done }))
    render(<BookProfilePanel book={book} disabled={false} onBusyChange={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Create profile' }))
    fireEvent.change(screen.getByLabelText('Domain'), { target: { value: 'Systems' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(screen.getByRole('button', { name: 'Saving profile…' })).toBeDisabled()
    await act(async () => resolve(profile))
  })

  it('retries loading and refreshes unknown outcomes without replay', async () => {
    vi.mocked(getBookProfile).mockRejectedValueOnce(new LibraryError('Load failed')).mockResolvedValueOnce(null)
    render(<BookProfilePanel book={book} disabled={false} onBusyChange={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Retry profile' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Create profile' }))
    fireEvent.change(screen.getByLabelText('Domain'), { target: { value: 'Systems' } })
    vi.mocked(putBookProfile).mockRejectedValue(new LibraryError('Unknown', 'outcome_unknown'))
    fireEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(await screen.findByText('Unknown')).toBeInTheDocument()
    await waitFor(() => expect(getBookProfile).toHaveBeenCalledTimes(3))
    expect(putBookProfile).toHaveBeenCalledTimes(1)
  })
})
