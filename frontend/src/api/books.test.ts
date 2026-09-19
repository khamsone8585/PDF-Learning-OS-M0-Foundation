import { act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { deleteBook, getBook, importBook, listBooks } from './books'

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
