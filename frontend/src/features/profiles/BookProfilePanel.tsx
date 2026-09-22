import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getBookProfile, putBookProfile } from '../../api/bookProfiles'
import type { BookProfile, BookProfileInput, Difficulty, Orientation } from '../../api/bookProfiles'
import { LibraryError } from '../../api/books'
import type { Book } from '../../api/books'

interface Props {
  book: Book
  disabled: boolean
  onBusyChange: (busy: boolean) => void
}

type Form = Record<keyof BookProfileInput, string>
const labels: Record<keyof BookProfileInput, string> = {
  domain: 'Domain', difficulty: 'Difficulty', prerequisites: 'Prerequisites',
  main_topics: 'Main topics', orientation: 'Theory/practice orientation', strengths: 'Strengths',
  weaknesses: 'Weaknesses', suggested_use: 'Suggested use',
}
const listFields = ['prerequisites', 'main_topics', 'strengths', 'weaknesses'] as const
const limits = { prerequisites: [25, 200], main_topics: [50, 200], strengths: [20, 500], weaknesses: [20, 500] }
const emptyForm: Form = { domain: '', difficulty: '', prerequisites: '', main_topics: '',
  orientation: '', strengths: '', weaknesses: '', suggested_use: '' }
const sourceLabels = { manual: 'Manually entered', ai_generated: 'AI generated',
  ai_assisted: 'AI assisted', derived: 'Derived' }
const displayLabels = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced',
  theory_heavy: 'Theory-heavy', balanced: 'Balanced', practice_heavy: 'Practice-heavy' }

const asError = (error: unknown) => error instanceof LibraryError
  ? error : new LibraryError('Book profile request failed.')

function toForm(profile: BookProfile | null): Form {
  if (!profile) return { ...emptyForm }
  return { domain: profile.domain || '', difficulty: profile.difficulty || '',
    prerequisites: profile.prerequisites.join('\n'), main_topics: profile.main_topics.join('\n'),
    orientation: profile.orientation || '', strengths: profile.strengths.join('\n'),
    weaknesses: profile.weaknesses.join('\n'), suggested_use: profile.suggested_use || '' }
}

function parse(form: Form): BookProfileInput {
  const lines = (value: string) => value.trim() ? value.split(/\r?\n/).map(item => item.trim()) : []
  return {
    domain: form.domain.trim() || null,
    difficulty: form.difficulty as Difficulty || null,
    prerequisites: lines(form.prerequisites),
    main_topics: lines(form.main_topics),
    orientation: form.orientation as Orientation || null,
    strengths: lines(form.strengths),
    weaknesses: lines(form.weaknesses),
    suggested_use: form.suggested_use.trim() || null,
  }
}

function validate(value: BookProfileInput) {
  if (!Object.values(value).some(item => Array.isArray(item) ? item.length : item)) {
    return 'Enter at least one profile field.'
  }
  if (value.domain && value.domain.length > 200) return 'Domain must contain at most 200 characters.'
  if (value.suggested_use && value.suggested_use.length > 2000) return 'Suggested use must contain at most 2,000 characters.'
  for (const field of listFields) {
    const [count, length] = limits[field]
    if (value[field].length > count) return `${labels[field]} may contain at most ${count} items.`
    if (value[field].some(item => !item || item.length > length)) return `Each ${labels[field].toLowerCase()} item must contain 1–${length} characters.`
    if (new Set(value[field].map(item => item.toLocaleLowerCase())).size !== value[field].length) {
      return `${labels[field]} must not contain duplicates.`
    }
  }
  return ''
}

export default function BookProfilePanel({ book, disabled, onBusyChange }: Props) {
  const [profile, setProfile] = useState<BookProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Form>({ ...emptyForm })
  const read = useRef<AbortController | null>(null)
  const mutation = useRef<AbortController | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)

  const load = useCallback(async () => {
    read.current?.abort()
    const controller = new AbortController()
    read.current = controller
    setLoading(true); setLoadError('')
    try {
      const result = await getBookProfile(book.id, controller.signal)
      if (!controller.signal.aborted) { setProfile(result); setForm(toForm(result)) }
      return !controller.signal.aborted
    } catch (error) {
      if (!controller.signal.aborted) setLoadError(asError(error).message)
      return false
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [book.id])

  useEffect(() => { void load(); return () => { read.current?.abort(); mutation.current?.abort() } }, [load])

  function change(field: keyof Form, value: string) {
    setForm(current => ({ ...current, [field]: value }))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (mutation.current) return
    const value = parse(form)
    const error = validate(value)
    if (error) { setSaveError(error); return }
    const controller = new AbortController()
    mutation.current = controller
    setSaving(true); onBusyChange(true); setSaveError(''); setNotice('')
    try {
      const result = await putBookProfile(book.id, value, controller.signal)
      if (controller.signal.aborted) return
      setProfile(result); setForm(toForm(result)); setEditing(false); setNotice('Book profile saved.')
      setTimeout(() => heading.current?.focus(), 0)
    } catch (caught) {
      if (controller.signal.aborted) return
      const failure = asError(caught)
      setSaveError(failure.message)
      if (failure.code === 'outcome_unknown' && await load()) setEditing(false)
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (!controller.signal.aborted) { setSaving(false); onBusyChange(false) }
    }
  }

  return <section className="book-profile" aria-labelledby="book-profile-heading">
    <h4 id="book-profile-heading" ref={heading} tabIndex={-1}>Book profile</h4>
    {loading && <p role="status">Loading book profile…</p>}
    {loadError && <div role="alert"><p>{loadError}</p><button onClick={() => void load()}>Retry profile</button></div>}
    {!loading && !loadError && !editing && !profile && <>
      <p>No profile has been recorded for this book.</p>
      <button disabled={disabled} onClick={() => { setEditing(true); setSaveError(''); setNotice('') }}>Create profile</button>
    </>}
    {!loading && !loadError && !editing && profile && <>
      <dl>{(Object.keys(labels) as Array<keyof BookProfileInput>).map(field => {
        const value = profile[field]
        const display = Array.isArray(value) ? (value.length ? value.join('; ') : 'Not recorded')
          : value ? (displayLabels[value as keyof typeof displayLabels] || value) : 'Not recorded'
        return <div key={field}><dt>{labels[field]}</dt><dd>{display}
          {profile.provenance[field] && <small> — {sourceLabels[profile.provenance[field]!]}</small>}</dd></div>
      })}</dl>
      <button disabled={disabled} onClick={() => { setForm(toForm(profile)); setEditing(true); setSaveError(''); setNotice('') }}>Edit profile</button>
    </>}
    {editing && <form onSubmit={submit}>
      <fieldset disabled={saving}>
        <legend>{profile ? 'Edit profile' : 'Create profile'}</legend>
        <label>Domain<input value={form.domain} maxLength={200} onChange={event => change('domain', event.target.value)} /></label>
        <label>Difficulty<select value={form.difficulty} onChange={event => change('difficulty', event.target.value)}>
          <option value="">Not recorded</option><option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
        </select></label>
        {listFields.slice(0, 2).map(field => <label key={field}>{labels[field]} (one per line)
          <textarea value={form[field]} onChange={event => change(field, event.target.value)} /></label>)}
        <label>Theory/practice orientation<select value={form.orientation} onChange={event => change('orientation', event.target.value)}>
          <option value="">Not recorded</option><option value="theory_heavy">Theory-heavy</option>
          <option value="balanced">Balanced</option><option value="practice_heavy">Practice-heavy</option>
        </select></label>
        {listFields.slice(2).map(field => <label key={field}>{labels[field]} (one per line)
          <textarea value={form[field]} onChange={event => change(field, event.target.value)} /></label>)}
        <label>Suggested use<textarea value={form.suggested_use} maxLength={2000}
          onChange={event => change('suggested_use', event.target.value)} /></label>
        <button type="button" disabled={saving} onClick={() => { setEditing(false); setForm(toForm(profile)); setSaveError('') }}>Cancel profile edit</button>
        <button type="submit" disabled={saving || disabled}>{saving ? 'Saving profile…' : 'Save profile'}</button>
      </fieldset>
    </form>}
    {saveError && <p role="alert">{saveError}</p>}
    <p role="status" aria-label="Book profile activity">{saving ? 'Saving book profile…' : notice}</p>
  </section>
}
