import { StrictMode } from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('../features/library/Library', () => ({ default: () => null }))

const ok = () => new Response(JSON.stringify({ status: 'ok', database: 'ok' }))

describe('local health status', () => {
  it('shows loading until the health request completes', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Checking local connection')
  })

  it('shows ready after a valid response and calls the health URL', async () => {
    const fetch = vi.fn().mockResolvedValue(ok())
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Ready'))
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/health', {
      signal: expect.any(AbortSignal),
    })
  })

  it.each([
    ['HTTP failure', () => Promise.resolve(new Response('{}', { status: 503 }))],
    ['network failure', () => Promise.reject(new TypeError('Failed to fetch'))],
    ['malformed JSON', () => Promise.resolve(new Response('not json'))],
    ['unexpected payload', () => Promise.resolve(new Response('{"status":"ok"}'))],
    ['null payload', () => Promise.resolve(new Response('null'))],
    ['extra fields', () => Promise.resolve(new Response('{"status":"ok","database":"ok","extra":true}'))],
  ])('shows unavailable on %s', async (_, response) => {
    vi.stubGlobal('fetch', vi.fn(response))
    render(<App />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Unavailable'))
  })

  it('times out after five seconds and ignores a late success', async () => {
    vi.useFakeTimers()
    let resolve!: (response: Response) => void
    const fetch = vi.fn(() => new Promise<Response>((done) => { resolve = done }))
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    await act(() => vi.advanceTimersByTimeAsync(5000))
    expect(screen.getByRole('status')).toHaveTextContent('Unavailable')
    await act(async () => resolve(ok()))
    expect(screen.getByRole('status')).toHaveTextContent('Unavailable')
  })

  it('aborts on unmount and clears its timeout', () => {
    vi.useFakeTimers()
    let signal: AbortSignal | undefined
    vi.stubGlobal('fetch', vi.fn((_: string, options: RequestInit) => {
      signal = options.signal as AbortSignal
      return new Promise(() => {})
    }))
    const { unmount } = render(<App />)
    unmount()
    expect(signal?.aborted).toBe(true)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('ignores the abandoned StrictMode request', async () => {
    let resolveOld!: (response: Response) => void
    const fetch = vi.fn()
      .mockImplementationOnce(() => new Promise<Response>((done) => { resolveOld = done }))
      .mockResolvedValueOnce(ok())
    vi.stubGlobal('fetch', fetch)
    render(<StrictMode><App /></StrictMode>)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Ready'))
    expect(fetch.mock.calls[0][1].signal.aborted).toBe(true)
    await act(async () => resolveOld(new Response('{}', { status: 503 })))
    expect(screen.getByRole('status')).toHaveTextContent('Ready')
  })
})
