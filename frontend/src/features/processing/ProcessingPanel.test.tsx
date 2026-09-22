import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProcessingPanel from './ProcessingPanel'
import { getBook, getChapters, LibraryError, processBook, updateChapters } from '../../api/books'
import type { Book, ChaptersResponse } from '../../api/books'

vi.mock('../../api/books', async (original) => ({
  ...await original<typeof import('../../api/books')>(),
  getBook: vi.fn(), getChapters: vi.fn(), processBook: vi.fn(), updateChapters: vi.fn(),
}))

const book: Book = { id: '00000000-0000-4000-8000-000000000001', title: 'Systems',
  original_filename: 'systems.pdf', author: null, edition: null, year: null, page_count: 3,
  size_bytes: 900, imported_at: '2026-09-19T00:00:00Z', file_available: true,
  processing_status: 'unprocessed', processing_error: null, processing_started_at: null,
  processed_at: null, has_processed_content: false, toc_status: null }

const fallback: ChaptersResponse = { book_id: book.id, processing_status: 'processed',
  content_available: true, toc_status: 'missing', structure_source: 'fallback', chapters: [
    { id: 'chapter', title: 'Full document', position: 0, level: 1,
      start_page: 1, end_page: 3, source: 'fallback' },
  ] }

beforeEach(() => {
  vi.mocked(getChapters).mockReset().mockResolvedValue({ ...fallback, processing_status: 'unprocessed',
    content_available: false, toc_status: null, structure_source: null, chapters: [] })
  vi.mocked(processBook).mockReset()
  vi.mocked(getBook).mockReset()
  vi.mocked(updateChapters).mockReset()
})

describe('processing panel', () => {
  it('processes a PDF and shows the resulting outline', async () => {
    const processed = { ...book, processing_status: 'processed' as const, processed_at: '2026-09-19T01:00:00Z',
      has_processed_content: true, toc_status: 'missing' as const }
    vi.mocked(processBook).mockResolvedValue(processed)
    vi.mocked(getChapters).mockResolvedValue(fallback)
    const changed = vi.fn()
    render(<ProcessingPanel book={book} disabled={false} onBookChange={changed} onBusyChange={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Process PDF' }))
    expect(await screen.findByText('Processed Systems.')).toBeInTheDocument()
    expect(changed).toHaveBeenCalledWith(processed)
    expect(await screen.findByText('Full document')).toBeInTheDocument()
  })

  it('explains OCR-required failures and refreshes durable state', async () => {
    const failed = { ...book, processing_status: 'failed' as const,
      processing_error: { code: 'ocr_required', message: 'This PDF needs OCR.' } }
    vi.mocked(processBook).mockRejectedValue(new LibraryError('This PDF needs OCR.', 'ocr_required'))
    vi.mocked(getBook).mockResolvedValue(failed)
    render(<ProcessingPanel book={book} disabled={false} onBookChange={vi.fn()} onBusyChange={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Process PDF' }))
    expect(await screen.findByText(/OCR is not supported in V0.1/)).toBeInTheDocument()
  })

  it('replaces fallback structure with flat manual sections', async () => {
    const processed = { ...book, processing_status: 'processed' as const, processed_at: 'stamp',
      has_processed_content: true, toc_status: 'missing' as const }
    const manual = { ...fallback, structure_source: 'manual' as const, chapters: [
      { ...fallback.chapters[0], title: 'Start', end_page: 1, source: 'manual' as const },
      { id: 'two', title: 'Finish', position: 1, level: 1, start_page: 2, end_page: 3, source: 'manual' as const },
    ] }
    vi.mocked(getChapters).mockResolvedValue(fallback)
    vi.mocked(updateChapters).mockResolvedValue(manual)
    render(<ProcessingPanel book={processed} disabled={false} onBookChange={vi.fn()} onBusyChange={vi.fn()} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Correct fallback sections' }))
    fireEvent.change(screen.getByLabelText('Section title'), { target: { value: 'Start' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add section' }))
    const titles = screen.getAllByLabelText('Section title')
    fireEvent.change(titles[1], { target: { value: 'Finish' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save sections' }))
    await waitFor(() => expect(updateChapters).toHaveBeenCalledWith(book.id, [
      { title: 'Start', start_page: 1 }, { title: 'Finish', start_page: 2 },
    ], expect.any(AbortSignal)))
    expect(await screen.findByText('Section structure saved.')).toBeInTheDocument()
  })
})
