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
  processing_status: 'unprocessed' | 'processing' | 'processed' | 'failed'
  processing_error: { code: string; message: string } | null
  processing_started_at: string | null
  processed_at: string | null
  has_processed_content: boolean
  toc_status: 'available' | 'partial' | 'missing' | 'invalid' | null
}

export interface Chapter {
  id: string
  title: string
  position: number
  level: number
  start_page: number
  end_page: number
  source: 'toc' | 'fallback' | 'manual'
}

export interface ChaptersResponse {
  book_id: string
  processing_status: Book['processing_status']
  content_available: boolean
  toc_status: Book['toc_status']
  structure_source: Chapter['source'] | null
  chapters: Chapter[]
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
    Number.isInteger(b.size_bytes) && Number(b.size_bytes) > 0 && typeof b.file_available === 'boolean' &&
    ['unprocessed', 'processing', 'processed', 'failed'].includes(String(b.processing_status)) &&
    (b.processing_error === null || (typeof b.processing_error === 'object' &&
      typeof (b.processing_error as Record<string, unknown>).code === 'string' &&
      typeof (b.processing_error as Record<string, unknown>).message === 'string')) &&
    ['processing_started_at', 'processed_at'].every(k => b[k] === null || typeof b[k] === 'string') &&
    typeof b.has_processed_content === 'boolean' &&
    (b.toc_status === null || ['available', 'partial', 'missing', 'invalid'].includes(String(b.toc_status)))
}

function isChapters(value: unknown): value is ChaptersResponse {
  if (!value || typeof value !== 'object') return false
  const response = value as Record<string, unknown>
  return typeof response.book_id === 'string' &&
    ['unprocessed', 'processing', 'processed', 'failed'].includes(String(response.processing_status)) &&
    typeof response.content_available === 'boolean' && Array.isArray(response.chapters) &&
    response.chapters.every(item => {
      if (!item || typeof item !== 'object') return false
      const chapter = item as Record<string, unknown>
      return ['id', 'title', 'source'].every(k => typeof chapter[k] === 'string') &&
        ['position', 'level', 'start_page', 'end_page'].every(k => Number.isInteger(chapter[k]))
    })
}

async function request(path: string, method: string, signal?: AbortSignal, body?: BodyInit,
                       timeout?: number, headers?: HeadersInit): Promise<unknown> {
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
      timer = setTimeout(abort, timeout ?? (mutation ? 120000 : 10000))
    })
    return await Promise.race([cancelled, (async () => {
      const response = await fetch(`${baseUrl}${path}`, {
        method, signal: controller.signal, ...(body ? { body } : {}), ...(headers ? { headers } : {}),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new LibraryError(data?.error?.message || 'Library request failed.',
          data?.error?.code, data?.error?.existing_book_id)
      }
      if (method === 'DELETE' && response.status === 204) return undefined
      if (response.status !== 200 && response.status !== 201) throw new Error('Unexpected status')
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

export async function processBook(id: string, signal?: AbortSignal): Promise<Book> {
  const result = await request(`/books/${encodeURIComponent(id)}/process`, 'POST', signal, undefined, 600000)
  if (!isBook(result)) throw new LibraryError('The result is unknown. Refresh before retrying.', 'outcome_unknown')
  return result
}

export async function getChapters(id: string, signal?: AbortSignal): Promise<ChaptersResponse> {
  const result = await request(`/books/${encodeURIComponent(id)}/chapters`, 'GET', signal)
  if (!isChapters(result)) throw new LibraryError('Unexpected chapter response.')
  return result
}

export async function updateChapters(id: string, sections: Array<{ title: string; start_page: number }>,
                                     signal?: AbortSignal): Promise<ChaptersResponse> {
  const result = await request(`/books/${encodeURIComponent(id)}/chapters`, 'PUT', signal,
    JSON.stringify({ sections }), 120000, { 'Content-Type': 'application/json' })
  if (!isChapters(result)) throw new LibraryError('The result is unknown. Refresh before retrying.', 'outcome_unknown')
  return result
}
