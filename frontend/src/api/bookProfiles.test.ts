import { describe, expect, it, vi } from 'vitest'
import { getBookProfile, putBookProfile } from './bookProfiles'
import type { BookProfile, BookProfileInput } from './bookProfiles'

const input: BookProfileInput = { domain: 'Computer science', difficulty: 'intermediate',
  prerequisites: ['Programming'], main_topics: ['Algorithms'], orientation: 'balanced',
  strengths: ['Examples'], weaknesses: [], suggested_use: 'Primary introduction' }
const provenance = { domain: 'manual', difficulty: 'manual', prerequisites: 'manual',
  main_topics: 'manual', orientation: 'manual', strengths: 'manual', weaknesses: null,
  suggested_use: 'manual' } as const
const profile: BookProfile = { book_id: 'book-id', ...input, provenance,
  created_at: '2026-09-22T00:00:00Z', updated_at: '2026-09-22T00:00:00Z' }

describe('book profile transport', () => {
  it('reads absent and populated profiles', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response('{"profile":null}', { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ profile }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    await expect(getBookProfile('book-id')).resolves.toBeNull()
    await expect(getBookProfile('book-id')).resolves.toEqual(profile)
    expect(fetch.mock.calls[0][0]).toContain('/books/book-id/profile')
  })

  it('sends the complete PUT contract', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(profile), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    await expect(putBookProfile('book-id', input)).resolves.toEqual(profile)
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'PUT', body: JSON.stringify(input) })
  })

  it('classifies malformed mutation responses as unknown', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 200 })))
    await expect(putBookProfile('book-id', input)).rejects.toMatchObject({ code: 'outcome_unknown' })
  })
})
