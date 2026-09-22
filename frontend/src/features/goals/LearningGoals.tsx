import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { Book } from '../../api/books'
import { LibraryError } from '../../api/books'
import { createGoal, getActiveGoal, replaceGoalBooks } from '../../api/learningGoals'
import type { LearningGoal } from '../../api/learningGoals'
import BookComparisonPanel from '../comparisons/BookComparisonPanel'

interface Props {
  books: Book[]
  disabled: boolean
  onBusyChange?: (busy: boolean) => void
  profileRefreshKey?: number
  onOpenBook?: (id: string) => void
}

const asError = (error: unknown) => error instanceof LibraryError
  ? error : new LibraryError('Learning goal request failed.')

export default function LearningGoals({ books, disabled, onBusyChange, profileRefreshKey, onOpenBook }: Props) {
  const [showComparison, setShowComparison] = useState(false)
  const [goal, setGoal] = useState<LearningGoal | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [mode, setMode] = useState<'create' | 'replace' | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [validation, setValidation] = useState('')
  const [actionError, setActionError] = useState('')
  const [notice, setNotice] = useState('')
  const [working, setWorking] = useState(false)
  const read = useRef<AbortController | null>(null)
  const mutation = useRef<AbortController | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)

  const load = useCallback(async () => {
    read.current?.abort()
    const controller = new AbortController()
    read.current = controller
    setLoading(true); setLoadError('')
    try {
      const active = await getActiveGoal(controller.signal)
      if (controller.signal.aborted) return
      setGoal(active)
      setMode(active ? null : 'create')
      if (!active) setSelected([])
    } catch (error) {
      if (!controller.signal.aborted) setLoadError(asError(error).message)
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    return () => { read.current?.abort(); mutation.current?.abort() }
  }, [load])

  function toggle(bookId: string) {
    setValidation('')
    setSelected(values => values.includes(bookId)
      ? values.filter(id => id !== bookId) : [...values, bookId])
  }

  function beginCreate() {
    setTitle(''); setDescription(''); setSelected([])
    setValidation(''); setActionError(''); setNotice(''); setMode('create')
  }

  function beginReplace() {
    if (!goal) return
    setSelected(goal.book_ids); setValidation(''); setActionError(''); setNotice('')
    setMode('replace')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (mutation.current) return
    if (mode === 'create' && (!title.trim() || title.trim().length > 200)) {
      setValidation('Enter a goal title between 1 and 200 characters.'); return
    }
    if (selected.length < 3 || selected.length > 5) {
      setValidation('Select between 3 and 5 books.'); return
    }
    const controller = new AbortController()
    mutation.current = controller
    setWorking(true); onBusyChange?.(true); setValidation(''); setActionError(''); setNotice('')
    try {
      const result = mode === 'replace' && goal
        ? await replaceGoalBooks(goal.id, selected, controller.signal)
        : await createGoal(title, description, selected, controller.signal)
      if (controller.signal.aborted) return
      setGoal(result); setMode(null)
      setNotice(mode === 'replace' ? 'Learning goal books updated.' : 'Active learning goal created.')
      setTimeout(() => heading.current?.focus(), 0)
    } catch (error) {
      if (controller.signal.aborted) return
      const failure = asError(error)
      setActionError(failure.message)
      if (failure.code === 'outcome_unknown') await load()
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (!controller.signal.aborted) { setWorking(false); onBusyChange?.(false) }
    }
  }

  const selectedBooks = goal?.book_ids.map(id => books.find(book => book.id === id)) || []
  const formDisabled = disabled || working

  return <section className="learning-goals" aria-labelledby="learning-goals-heading">
    <h3 id="learning-goals-heading" ref={heading} tabIndex={-1}>Learning goal</h3>
    {loading && <p role="status">Loading active learning goal…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => void load()}>Retry learning goal</button></div>}
    {!loading && !loadError && goal && mode === null && <div>
      <p><strong>{goal.title}</strong></p>
      {goal.description && <p>{goal.description}</p>}
      <p>Selected books:</p>
      <ul>{selectedBooks.map((book, index) => <li key={goal.book_ids[index]}>
        {book?.title || 'Unavailable book'}
      </li>)}</ul>
      <button disabled={formDisabled} onClick={beginReplace}>Change selected books</button>
      <button disabled={formDisabled} onClick={beginCreate}>Start a new goal</button>
      <button disabled={formDisabled} onClick={() => setShowComparison(true)}>Compare selected books</button>
      {showComparison && <BookComparisonPanel key={goal.id} goal={goal} disabled={disabled}
        refreshKey={profileRefreshKey} onBusyChange={onBusyChange} onOpenBook={onOpenBook} />}
    </div>}
    {!loading && !loadError && mode === 'create' && goal &&
      <p className="goal-warning">Creating this goal will make “{goal.title}” inactive.</p>}
    {!loading && !loadError && mode && <form onSubmit={event => void submit(event)}>
      <fieldset disabled={formDisabled}>
        <legend>{mode === 'replace' ? 'Change selected books' : 'Create an active learning goal'}</legend>
        {mode === 'create' && <>
          <label>Goal title<input value={title} maxLength={200} required
            onChange={event => setTitle(event.target.value)} /></label>
          <label>Description (optional)<textarea value={description} maxLength={2000}
            onChange={event => setDescription(event.target.value)} /></label>
        </>}
        <p id="goal-selection-help">Select 3–5 books. {selected.length} selected.</p>
        {books.length < 3 && <p>Import at least three books before creating a learning goal.</p>}
        <div className="goal-book-selection" aria-describedby="goal-selection-help">
          {books.map(book => {
            const checked = selected.includes(book.id)
            return <label key={book.id}>
              <input type="checkbox" checked={checked}
                disabled={formDisabled || (!checked && selected.length >= 5)}
                onChange={() => toggle(book.id)} />
              <span>{book.title}</span>
            </label>
          })}
        </div>
        {validation && <p role="alert">{validation}</p>}
        {mode === 'replace' && <button type="button" onClick={() => {
          setMode(null); setValidation(''); setActionError('')
        }}>Cancel</button>}
        {mode === 'create' && goal && <button type="button" onClick={() => {
          setMode(null); setValidation(''); setActionError('')
        }}>Cancel new goal</button>}
        <button type="submit" disabled={formDisabled || books.length < 3}>
          {working ? 'Saving…' : mode === 'replace' ? 'Save selected books' : 'Create learning goal'}
        </button>
      </fieldset>
    </form>}
    {actionError && <p role="alert">{actionError}</p>}
    <p role="status" aria-label="Learning goal activity">{working ? 'Saving learning goal…' : notice}</p>
  </section>
}
