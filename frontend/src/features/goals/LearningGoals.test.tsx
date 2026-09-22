import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LibraryError } from '../../api/books'
import type { Book } from '../../api/books'
import { createGoal, getActiveGoal, replaceGoalBooks } from '../../api/learningGoals'
import type { LearningGoal } from '../../api/learningGoals'
import LearningGoals from './LearningGoals'

vi.mock('../../api/learningGoals', () => ({
  getActiveGoal: vi.fn(), createGoal: vi.fn(), replaceGoalBooks: vi.fn(),
}))

const books: Book[] = Array.from({ length: 6 }, (_, index) => ({
  id: `00000000-0000-4000-8000-00000000000${index + 1}`,
  title: `Book ${index + 1}`, original_filename: `book-${index + 1}.pdf`, author: null,
  edition: null, year: null, page_count: 10, imported_at: '2026-09-22T00:00:00Z',
  size_bytes: 100, file_available: true, processing_status: 'unprocessed',
  processing_error: null, processing_started_at: null, processed_at: null,
  has_processed_content: false, toc_status: null,
}))
const goal: LearningGoal = { id: '10000000-0000-4000-8000-000000000001', title: 'Systems',
  description: 'Learn the foundations.', is_active: true,
  created_at: '2026-09-22T00:00:00Z', updated_at: '2026-09-22T00:00:00Z',
  book_ids: books.slice(0, 3).map(book => book.id) }

beforeEach(() => {
  vi.mocked(getActiveGoal).mockReset().mockResolvedValue(null)
  vi.mocked(createGoal).mockReset().mockResolvedValue(goal)
  vi.mocked(replaceGoalBooks).mockReset().mockResolvedValue(goal)
})

async function select(count: number) {
  for (let index = 0; index < count; index++) {
    fireEvent.click(screen.getByRole('checkbox', { name: books[index].title }))
  }
}

describe('learning goals UI', () => {
  it('guides creation and validates the three-book minimum', async () => {
    render(<LearningGoals books={books} disabled={false} />)
    await screen.findByRole('group', { name: 'Create an active learning goal' })
    fireEvent.change(screen.getByLabelText('Goal title'), { target: { value: 'Systems' } })
    await select(2)
    fireEvent.click(screen.getByRole('button', { name: 'Create learning goal' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Select between 3 and 5 books')
    expect(createGoal).not.toHaveBeenCalled()
  })

  it('creates a goal with three selected books and focuses its heading', async () => {
    render(<LearningGoals books={books} disabled={false} />)
    await screen.findByLabelText('Goal title')
    fireEvent.change(screen.getByLabelText('Goal title'), { target: { value: 'Systems' } })
    fireEvent.change(screen.getByLabelText('Description (optional)'), {
      target: { value: 'Learn the foundations.' } })
    await select(3)
    fireEvent.click(screen.getByRole('button', { name: 'Create learning goal' }))
    await screen.findByText('Active learning goal created.')
    expect(createGoal).toHaveBeenCalledWith('Systems', 'Learn the foundations.', goal.book_ids,
      expect.any(AbortSignal))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Learning goal' })).toHaveFocus())
  })

  it('prevents selecting a sixth book', async () => {
    render(<LearningGoals books={books} disabled={false} />)
    await screen.findByLabelText('Goal title')
    await select(5)
    expect(screen.getByText('Select 3–5 books. 5 selected.')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: books[5].title })).toBeDisabled()
  })

  it('shows the active goal and replaces its complete selection', async () => {
    vi.mocked(getActiveGoal).mockResolvedValue(goal)
    vi.mocked(replaceGoalBooks).mockResolvedValue({ ...goal,
      book_ids: [books[1].id, books[2].id, books[3].id] })
    render(<LearningGoals books={books} disabled={false} />)
    await screen.findByText(goal.title)
    expect(screen.getByText(goal.description!)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Change selected books' }))
    fireEvent.click(screen.getByRole('checkbox', { name: books[0].title }))
    fireEvent.click(screen.getByRole('checkbox', { name: books[3].title }))
    fireEvent.click(screen.getByRole('button', { name: 'Save selected books' }))
    await screen.findByText('Learning goal books updated.')
    expect(replaceGoalBooks).toHaveBeenCalledWith(goal.id,
      [books[1].id, books[2].id, books[3].id], expect.any(AbortSignal))
  })

  it('warns before starting a new goal and can cancel', async () => {
    vi.mocked(getActiveGoal).mockResolvedValue(goal)
    render(<LearningGoals books={books} disabled={false} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Start a new goal' }))
    expect(screen.getByText(/will make “Systems” inactive/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel new goal' }))
    expect(screen.getByText(goal.title)).toBeInTheDocument()
  })

  it('refreshes an unknown result without replaying the mutation', async () => {
    vi.mocked(createGoal).mockRejectedValue(new LibraryError('Unknown result', 'outcome_unknown'))
    vi.mocked(getActiveGoal).mockResolvedValueOnce(null).mockResolvedValueOnce(goal)
    render(<LearningGoals books={books} disabled={false} />)
    await screen.findByLabelText('Goal title')
    fireEvent.change(screen.getByLabelText('Goal title'), { target: { value: 'Systems' } })
    await select(3)
    fireEvent.click(screen.getByRole('button', { name: 'Create learning goal' }))
    expect(await screen.findByText('Unknown result')).toBeInTheDocument()
    await waitFor(() => expect(getActiveGoal).toHaveBeenCalledTimes(2))
    expect(createGoal).toHaveBeenCalledTimes(1)
  })

  it('preserves selections after a server error and supports cancel', async () => {
    vi.mocked(getActiveGoal).mockResolvedValue(goal)
    vi.mocked(replaceGoalBooks).mockRejectedValue(new LibraryError('Selection failed'))
    render(<LearningGoals books={books} disabled={false} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Change selected books' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save selected books' }))
    expect(await screen.findByText('Selection failed')).toBeInTheDocument()
    expect(within(screen.getByRole('group', { name: 'Change selected books' }))
      .getAllByRole('checkbox').filter(item => (item as HTMLInputElement).checked)).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByText(goal.title)).toBeInTheDocument()
  })

  it('disables save while a mutation is active', async () => {
    let resolve!: (value: LearningGoal) => void
    vi.mocked(createGoal).mockImplementation(() => new Promise(done => { resolve = done }))
    render(<LearningGoals books={books} disabled={false} />)
    await screen.findByLabelText('Goal title')
    fireEvent.change(screen.getByLabelText('Goal title'), { target: { value: 'Systems' } })
    await select(3)
    fireEvent.click(screen.getByRole('button', { name: 'Create learning goal' }))
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
    await act(async () => resolve(goal))
  })
})
