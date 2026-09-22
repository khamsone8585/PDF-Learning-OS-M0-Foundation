import { act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { deleteBook, getBook, importBook, listBooks, processBook, updateChapters } from './books'

const book = { id: 'id', title: 'Book', original_filename: 'book.pdf', author: null, edition: null,
  year: null, page_count: 2, imported_at: '2026-09-19T00:00:00Z', size_bytes: 10,
  file_available: true, processing_status: 'processed', processing_error: null,
  processing_started_at: '2026-09-19T00:00:00Z', processed_at: '2026-09-19T00:01:00Z',
  has_processed_content: true, toc_status: 'missing' }

describe('library transport', () => {
  it('validates list responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"books":[{}]}')))
    await expect(listBooks()).rejects.toThrow('Unexpected library response')
  })
  it('uses the configured endpoint and handles structured duplicates', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: {
      code: 'duplicate_book', message: 'Duplicate', existing_book_id: 'existing',
    } }), { status: 409 }))
    vi.stubGlobal('fetch', fetch)
    await expect(importBook(new FormData())).rejects.toMatchObject({ code: 'duplicate_book', existingBookId: 'existing' })
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:8000/books')
  })
  it('accepts empty 204 deletion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(deleteBook('id')).resolves.toBeUndefined()
  })
  it('uses processing and correction contracts', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(book), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ book_id: 'id', processing_status: 'processed',
        content_available: true, toc_status: 'missing', structure_source: 'manual', chapters: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    await expect(processBook('id')).resolves.toMatchObject({ processing_status: 'processed' })
    await expect(updateChapters('id', [{ title: 'Start', start_page: 1 }])).resolves.toMatchObject({ structure_source: 'manual' })
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(fetch.mock.calls[1][1]).toMatchObject({ method: 'PUT', body: JSON.stringify({ sections: [{ title: 'Start', start_page: 1 }] }) })
  })
  it.each([['read', 10000], ['mutation', 120000]] as const)('bounds stalled %s requests', async (kind, delay) => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    const operation = kind === 'read' ? getBook('id') : importBook(new FormData())
    const assertion = expect(operation).rejects.toMatchObject({ code: kind === 'read' ? 'request_timeout' : 'outcome_unknown' })
    await act(() => vi.advanceTimersByTimeAsync(delay))
    await assertion
    expect(vi.getTimerCount()).toBe(0)
  })
  it('aborts reads on unmount signal', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    const controller = new AbortController()
    const operation = listBooks(controller.signal)
    controller.abort()
    await expect(operation).rejects.toMatchObject({ code: 'request_timeout' })
  })
})
