import { describe, expect, it, vi } from 'vitest'
import { createGoal, getActiveGoal, replaceGoalBooks } from './learningGoals'

const goal = { id: 'goal-id', title: 'Systems', description: null, is_active: true,
  created_at: '2026-09-22T00:00:00Z', updated_at: '2026-09-22T00:00:00Z',
  book_ids: ['one', 'two', 'three'] }

describe('learning goal transport', () => {
  it('reads an empty or populated active goal', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response('{"goal":null}', { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ goal }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    await expect(getActiveGoal()).resolves.toBeNull()
    await expect(getActiveGoal()).resolves.toEqual(goal)
  })

  it('uses create and complete replacement contracts', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(goal), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(goal), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    await createGoal('Systems', '', goal.book_ids)
    await replaceGoalBooks(goal.id, goal.book_ids)
    expect(fetch.mock.calls[0][0]).toBe('http://127.0.0.1:8000/learning-goals')
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'POST', body: JSON.stringify({
      title: 'Systems', description: null, book_ids: goal.book_ids }) })
    expect(fetch.mock.calls[1][0]).toContain('/learning-goals/goal-id/books')
    expect(fetch.mock.calls[1][1]).toMatchObject({ method: 'PUT' })
  })

  it('rejects malformed responses as unknown mutation outcomes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 201 })))
    await expect(createGoal('Systems', '', goal.book_ids)).rejects.toMatchObject({
      code: 'outcome_unknown' })
  })
})
