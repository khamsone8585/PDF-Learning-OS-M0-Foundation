import { LibraryError, request } from './books'

export interface LearningGoal {
  id: string
  title: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  book_ids: string[]
}

function isGoal(value: unknown): value is LearningGoal {
  if (!value || typeof value !== 'object') return false
  const goal = value as Record<string, unknown>
  return ['id', 'title', 'created_at', 'updated_at'].every(key => typeof goal[key] === 'string') &&
    (goal.description === null || typeof goal.description === 'string') &&
    typeof goal.is_active === 'boolean' && Array.isArray(goal.book_ids) &&
    goal.book_ids.every(id => typeof id === 'string')
}

export async function getActiveGoal(signal?: AbortSignal): Promise<LearningGoal | null> {
  const result = await request('/learning-goals/active', 'GET', signal)
  if (!result || typeof result !== 'object' || !('goal' in result)) {
    throw new LibraryError('Unexpected learning goal response.')
  }
  const goal = result.goal
  if (goal !== null && !isGoal(goal)) throw new LibraryError('Unexpected learning goal response.')
  return goal
}

export async function createGoal(title: string, description: string, bookIds: string[],
                                 signal?: AbortSignal): Promise<LearningGoal> {
  const result = await request('/learning-goals', 'POST', signal,
    JSON.stringify({ title, description: description || null, book_ids: bookIds }),
    120000, { 'Content-Type': 'application/json' })
  if (!isGoal(result)) throw new LibraryError(
    'The result is unknown. Refresh the active goal before retrying.', 'outcome_unknown')
  return result
}

export async function replaceGoalBooks(goalId: string, bookIds: string[],
                                       signal?: AbortSignal): Promise<LearningGoal> {
  const result = await request(`/learning-goals/${encodeURIComponent(goalId)}/books`, 'PUT', signal,
    JSON.stringify({ book_ids: bookIds }), 120000, { 'Content-Type': 'application/json' })
  if (!isGoal(result)) throw new LibraryError(
    'The result is unknown. Refresh the active goal before retrying.', 'outcome_unknown')
  return result
}
