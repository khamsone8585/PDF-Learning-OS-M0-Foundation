import { LibraryError, request } from './books'

export type Difficulty = 'beginner' | 'intermediate' | 'advanced'
export type Orientation = 'theory_heavy' | 'balanced' | 'practice_heavy'
export type ProfileSource = 'manual' | 'ai_generated' | 'ai_assisted' | 'derived'

export interface BookProfileInput {
  domain: string | null
  difficulty: Difficulty | null
  prerequisites: string[]
  main_topics: string[]
  orientation: Orientation | null
  strengths: string[]
  weaknesses: string[]
  suggested_use: string | null
}

export interface BookProfile extends BookProfileInput {
  book_id: string
  provenance: Record<keyof BookProfileInput, ProfileSource | null>
  created_at: string
  updated_at: string
}

const fields: Array<keyof BookProfileInput> = [
  'domain', 'difficulty', 'prerequisites', 'main_topics', 'orientation',
  'strengths', 'weaknesses', 'suggested_use',
]
const sources = ['manual', 'ai_generated', 'ai_assisted', 'derived']

function isProfile(value: unknown): value is BookProfile {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  const provenance = item.provenance
  return typeof item.book_id === 'string' && typeof item.created_at === 'string' &&
    typeof item.updated_at === 'string' &&
    ['domain', 'suggested_use'].every(key => item[key] === null || typeof item[key] === 'string') &&
    (item.difficulty === null || ['beginner', 'intermediate', 'advanced'].includes(String(item.difficulty))) &&
    (item.orientation === null || ['theory_heavy', 'balanced', 'practice_heavy'].includes(String(item.orientation))) &&
    ['prerequisites', 'main_topics', 'strengths', 'weaknesses'].every(key =>
      Array.isArray(item[key]) && (item[key] as unknown[]).every(entry => typeof entry === 'string')) &&
    !!provenance && typeof provenance === 'object' && fields.every(key => {
      const source = (provenance as Record<string, unknown>)[key]
      return source === null || sources.includes(String(source))
    })
}

export async function getBookProfile(bookId: string, signal?: AbortSignal): Promise<BookProfile | null> {
  const result = await request(`/books/${encodeURIComponent(bookId)}/profile`, 'GET', signal)
  if (!result || typeof result !== 'object' || !('profile' in result)) {
    throw new LibraryError('Unexpected book profile response.')
  }
  const profile = result.profile
  if (profile !== null && !isProfile(profile)) throw new LibraryError('Unexpected book profile response.')
  return profile
}

export async function putBookProfile(bookId: string, profile: BookProfileInput,
                                     signal?: AbortSignal): Promise<BookProfile> {
  const result = await request(`/books/${encodeURIComponent(bookId)}/profile`, 'PUT', signal,
    JSON.stringify(profile), 120000, { 'Content-Type': 'application/json' })
  if (!isProfile(result)) throw new LibraryError(
    'The result is unknown. Reload the profile before retrying.', 'outcome_unknown')
  return result
}
