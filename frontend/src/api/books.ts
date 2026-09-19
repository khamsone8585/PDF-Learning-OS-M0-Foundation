const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export interface Book {
  id: string
  title: string
  original_filename: string
  author: string | null
  edition: string | null
  year: number | null
  page_count: number
  imported_at: string
  size_bytes: number
  file_available: boolean
}

export class LibraryError extends Error {
  constructor(message: string, public code = 'request_failed', public existingBookId?: string) {
    super(message)
  }
}

function isBook(value: unknown): value is Book {
  if (!value || typeof value !== 'object') return false
  const b = value as Record<string, unknown>
  return ['id', 'title', 'original_filename', 'imported_at'].every(k => typeof b[k] === 'string') &&
    ['author', 'edition'].every(k => b[k] === null || typeof b[k] === 'string') &&
    (b.year === null || (Number.isInteger(b.year) && Number(b.year) >= 1 && Number(b.year) <= 9999)) &&
    Number.isInteger(b.page_count) && Number(b.page_count) > 0 &&
    Number.isInteger(b.size_bytes) && Number(b.size_bytes) > 0 && typeof b.file_available === 'boolean'
}

async function request(path: string, method: string, signal?: AbortSignal, body?: FormData): Promise<unknown> {
  const mutation = method !== 'GET'
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) abort()
  let timer: ReturnType<typeof setTimeout> | undefined
  let onAbort: (() => void) | undefined
  try {
    const cancelled = new Promise<never>((_, reject) => {
      onAbort = () => reject(new LibraryError(mutation
        ? 'The result is unknown. Refresh the library before retrying.'
        : 'The request stopped or timed out. Please retry.', mutation ? 'outcome_unknown' : 'request_timeout'))
      controller.signal.addEventListener('abort', onAbort, { once: true })
      if (controller.signal.aborted) onAbort()
      timer = setTimeout(abort, mutation ? 120000 : 10000)
    })
    return await Promise.race([cancelled, (async () => {
      const response = await fetch(`${baseUrl}${path}`, { method, signal: controller.signal, ...(body ? { body } : {}) })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new LibraryError(data?.error?.message || 'Library request failed.',
          data?.error?.code, data?.error?.existing_book_id)
      }
      if (method === 'DELETE' && response.status === 204) return undefined
      if (response.status !== (method === 'POST' ? 201 : 200)) throw new Error('Unexpected status')
      return await response.json()
    })()])
  } catch (error) {
    if (error instanceof LibraryError) throw error
    throw new LibraryError(mutation
      ? 'The result is unknown. Refresh the library before retrying.'
      : 'Cannot read the library. Check the backend and retry.', mutation ? 'outcome_unknown' : 'request_failed')
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
    if (onAbort) controller.signal.removeEventListener('abort', onAbort)
  }
}

export async function listBooks(signal?: AbortSignal): Promise<Book[]> {
  const result = await request('/books', 'GET', signal)
  if (!result || typeof result !== 'object' || !('books' in result) ||
      !Array.isArray(result.books) || !result.books.every(isBook)) throw new LibraryError('Unexpected library response.')
  return result.books
}

export async function getBook(id: string, signal?: AbortSignal): Promise<Book> {
  const result = await request(`/books/${encodeURIComponent(id)}`, 'GET', signal)
  if (!isBook(result)) throw new LibraryError('Unexpected book response.')
  return result
}

export async function importBook(data: FormData, signal?: AbortSignal): Promise<Book> {
  const result = await request('/books', 'POST', signal, data)
  if (!isBook(result)) throw new LibraryError('The result is unknown. Refresh the library before retrying.', 'outcome_unknown')
  return result
}

export async function deleteBook(id: string, signal?: AbortSignal): Promise<void> {
  await request(`/books/${encodeURIComponent(id)}`, 'DELETE', signal)
}
