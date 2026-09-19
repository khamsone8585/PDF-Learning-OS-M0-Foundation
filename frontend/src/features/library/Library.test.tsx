import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Library from './Library'
import { deleteBook, getBook, importBook, LibraryError, listBooks } from '../../api/books'
import type { Book } from '../../api/books'

vi.mock('../../api/books', async (original) => ({
  ...await original<typeof import('../../api/books')>(),
  listBooks: vi.fn(), getBook: vi.fn(), importBook: vi.fn(), deleteBook: vi.fn(),
}))
const book: Book = { id: '00000000-0000-4000-8000-000000000001', title: 'Algorithms',
  original_filename: 'algorithms.pdf', author: null, edition: null, year: null,
  page_count: 12, size_bytes: 500, imported_at: '2026-09-18T10:00:00Z', file_available: true }

beforeEach(() => {
  vi.mocked(listBooks).mockReset().mockResolvedValue([])
  vi.mocked(getBook).mockReset().mockResolvedValue(book)
  vi.mocked(importBook).mockReset().mockResolvedValue(book)
  vi.mocked(deleteBook).mockReset().mockResolvedValue(undefined)
})

function selectFile() {
  fireEvent.change(screen.getByLabelText('PDF file'), { target: { files: [new File(['pdf'], 'book.pdf', { type: 'application/pdf' })] } })
  // jsdom FormData does not consistently include a synthetic input File.
  const RealFormData = globalThis.FormData
  vi.stubGlobal('FormData', class extends RealFormData {
    constructor(form?: HTMLFormElement) { super(form); this.set('file', new File(['pdf'], 'book.pdf')) }
  })
}

async function openDetails() {
  vi.mocked(listBooks).mockResolvedValue([book])
  render(<Library />)
  fireEvent.click(await screen.findByRole('button', { name: book.title }))
  await screen.findByRole('heading', { name: book.title })
}

describe('library UI', () => {
  it('loads and shows an empty library', async () => {
    render(<Library />)
    expect(screen.getByText('Loading books…')).toBeInTheDocument()
    expect(await screen.findByText(/No books yet/)).toBeInTheDocument()
  })

  it('retries a failed list', async () => {
    vi.mocked(listBooks).mockRejectedValueOnce(new LibraryError('Storage unavailable'))
    render(<Library />)
    fireEvent.click(await screen.findByRole('button', { name: 'Retry library' }))
    expect(await screen.findByText(/No books yet/)).toBeInTheDocument()
  })

  it('imports optional metadata and opens details', async () => {
    render(<Library />)
    await screen.findByText(/No books yet/)
    selectFile()
    fireEvent.change(screen.getByLabelText('Title (optional)'), { target: { value: 'Algorithms' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Import PDF' }).closest('form')!)
    expect(await screen.findByRole('heading', { name: 'Algorithms' })).toBeInTheDocument()
    expect(vi.mocked(importBook).mock.calls[0][0].get('title')).toBe('Algorithms')
    expect(screen.getByText('algorithms.pdf')).toBeInTheDocument()
    expect(screen.getAllByText('Not provided')).toHaveLength(3)
  })

  it('disables resubmission while import runs', async () => {
    let complete!: (book: Book) => void
    vi.mocked(importBook).mockImplementation(() => new Promise(resolve => { complete = resolve }))
    render(<Library />); await screen.findByText(/No books yet/); selectFile()
    fireEvent.submit(screen.getByRole('button', { name: 'Import PDF' }).closest('form')!)
    expect(screen.getByRole('button', { name: 'Importing…' })).toBeDisabled()
    await act(async () => complete(book))
  })

  it('opens an existing book from duplicate error', async () => {
    vi.mocked(importBook).mockRejectedValue(new LibraryError('Already imported', 'duplicate_book', book.id))
    render(<Library />); await screen.findByText(/No books yet/); selectFile()
    fireEvent.submit(screen.getByRole('button', { name: 'Import PDF' }).closest('form')!)
    fireEvent.click(await screen.findByRole('button', { name: 'Open existing book' }))
    expect(await screen.findByRole('heading', { name: book.title })).toBeInTheDocument()
  })

  it('focuses Cancel and cancellation never deletes', async () => {
    await openDetails()
    fireEvent.click(screen.getByRole('button', { name: 'Remove book' }))
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(deleteBook).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Remove book' })).toHaveFocus())
  })

  it('deletes only after confirmation and refreshes the list', async () => {
    await openDetails()
    vi.mocked(listBooks).mockResolvedValue([])
    fireEvent.click(screen.getByRole('button', { name: 'Remove book' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete book' }))
    expect(await screen.findByText(/No books yet/)).toBeInTheDocument()
    expect(deleteBook).toHaveBeenCalledWith(book.id, expect.any(AbortSignal))
    expect(screen.queryByRole('heading', { name: book.title })).not.toBeInTheDocument()
  })

  it('retains details and allows cleanup retry', async () => {
    await openDetails()
    vi.mocked(deleteBook).mockRejectedValueOnce(new LibraryError('Cleanup pending', 'deletion_cleanup_pending'))
    fireEvent.click(screen.getByRole('button', { name: 'Remove book' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete book' }))
    expect(await screen.findByText('Cleanup pending')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: book.title })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry deletion' }))
    await waitFor(() => expect(deleteBook).toHaveBeenCalledTimes(2))
  })

  it('shows missing-file details and detail errors', async () => {
    vi.mocked(getBook).mockResolvedValue({ ...book, file_available: false })
    await openDetails()
    expect(screen.getByText(/The local PDF is missing/)).toBeInTheDocument()
    vi.mocked(getBook).mockRejectedValue(new LibraryError('Book not found'))
    fireEvent.click(screen.getByRole('button', { name: book.title }))
    expect(await screen.findByText(/Book not found/)).toBeInTheDocument()
  })

  it('refreshes after an unknown import outcome without replaying it', async () => {
    vi.mocked(importBook).mockRejectedValue(new LibraryError('Unknown result', 'outcome_unknown'))
    render(<Library />); await screen.findByText(/No books yet/); selectFile()
    fireEvent.submit(screen.getByRole('button', { name: 'Import PDF' }).closest('form')!)
    expect(await screen.findByText('Unknown result')).toBeInTheDocument()
    expect(listBooks).toHaveBeenCalledTimes(2)
    expect(importBook).toHaveBeenCalledTimes(1)
  })

  it('ignores a late details response after a newer selection', async () => {
    let resolveOld!: (b: Book) => void
    vi.mocked(listBooks).mockResolvedValue([book, { ...book, id: 'second', title: 'Second' }])
    vi.mocked(getBook).mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce({ ...book, id: 'second', title: 'Second' })
    render(<Library />)
    fireEvent.click(await screen.findByRole('button', { name: book.title }))
    fireEvent.click(screen.getByRole('button', { name: 'Second' }))
    await screen.findByRole('heading', { name: 'Second' })
    await act(async () => resolveOld(book))
    expect(within(screen.getByRole('article')).getByRole('heading')).toHaveTextContent('Second')
  })
})
