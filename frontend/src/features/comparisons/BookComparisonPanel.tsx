import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { LibraryError } from '../../api/books'
import { evidenceKey, evidenceOptions, getComparison, putComparison, roleLabels } from '../../api/bookComparisons'
import type { Assessment, Comparison, Evidence, Judgment, Preview, Role } from '../../api/bookComparisons'
import type { LearningGoal } from '../../api/learningGoals'
import ComparisonFacts from './ComparisonFacts'

type Draft = Omit<Judgment, 'role'> & { role: Role | '' }
interface Editor { preview: Preview; token: string; revision: number | null; books: Draft[] }
interface Props {
  goal: LearningGoal; disabled: boolean; refreshKey?: number
  onBusyChange?: (busy: boolean) => void; onOpenBook?: (id: string) => void
}
const failure = (error: unknown) => error instanceof LibraryError ? error : new LibraryError('Comparison request failed.')
const empty = (id: string): Draft => ({ book_id: id, role: '', rationale: '',
  relevance: { category: 'unknown', explanation: '' }, depth: null, practice: null,
  focus_topics: [], evidence_refs: [], reviewed: false })
const depthLabels = { overview: 'Overview', working_detail: 'Working detail', deep_treatment: 'Deep treatment' }
const practiceLabels = { limited: 'Limited', some: 'Some', substantial: 'Substantial' }

function AssessmentEditor({ label, value, options, onChange }: {
  label: string; value: Assessment | null; options: Record<string, string>
  onChange: (value: Assessment | null) => void
}) {
  return <><label>{label}<select value={value?.category || ''} onChange={event =>
    onChange(event.target.value ? { category: event.target.value, explanation: value?.explanation || '' } : null)}>
    <option value="">Unknown / not assessed</option>
    {Object.entries(options).map(([key, title]) => <option value={key} key={key}>{title}</option>)}
  </select></label>
    {value && <label>{label} explanation<textarea required maxLength={1000} value={value.explanation}
      onChange={event => onChange({ ...value, explanation: event.target.value })} /></label>}</>
}

export default function BookComparisonPanel({ goal, disabled, refreshKey = 0, onBusyChange, onOpenBook }: Props) {
  const [data, setData] = useState<Comparison | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editor, setEditor] = useState<Editor | null>(null)
  const [saving, setSaving] = useState(false)
  const read = useRef<AbortController | null>(null)
  const mutation = useRef<AbortController | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const load = useCallback(async () => {
    read.current?.abort()
    const controller = new AbortController()
    read.current = controller
    setLoading(true)
    try {
      const result = await getComparison(goal.id, controller.signal)
      if (!controller.signal.aborted) setData(result)
    } catch (caught) {
      if (!controller.signal.aborted) setError(failure(caught).message)
    } finally { if (!controller.signal.aborted) setLoading(false) }
  }, [goal.id])
  useEffect(() => {
    void load()
    const refresh = () => { if (!mutation.current) void load() }
    window.addEventListener('focus', refresh)
    return () => { read.current?.abort(); window.removeEventListener('focus', refresh) }
  }, [load, goal.updated_at, refreshKey])
  useEffect(() => () => mutation.current?.abort(), [])
  const focusHeading = () => setTimeout(() => heading.current?.focus(), 0)

  function begin() {
    if (!data?.current || !data.input_token) return
    const prior = editor?.books || data.saved?.books || []
    const books = data.current.books.map(book => {
      const existing = prior.find(j => j.book_id === book.book_id)
      if (!existing) return empty(book.book_id)
      return { book_id: existing.book_id, role: existing.role, rationale: existing.rationale,
        relevance: { ...existing.relevance }, depth: existing.depth ? { ...existing.depth } : null,
        practice: existing.practice ? { ...existing.practice } : null, focus_topics: [...existing.focus_topics],
        evidence_refs: [...existing.evidence_refs], reviewed: false }
    })
    setEditor({ preview: data.current, token: data.input_token, revision: data.saved?.revision ?? null, books })
    setError(''); setNotice('Review every book. Existing judgments are retained for your review.')
    focusHeading()
  }
  function change(id: string, values: Partial<Draft>) {
    setEditor(current => current && ({ ...current, books: current.books.map(book =>
      book.book_id === id ? { ...book, ...values } : book) }))
  }
  const changed = !!editor && !!data && (editor.token !== data.input_token ||
    editor.revision !== (data.saved?.revision ?? null))

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!editor || mutation.current || disabled) return
    if (changed) { setError('Inputs or saved results changed. Review with current inputs before saving.'); return }
    for (const j of editor.books) {
      const book = editor.preview.books.find(b => b.book_id === j.book_id)!
      const options = new Set(evidenceOptions(book, editor.preview).map(o => evidenceKey(o.value)))
      if (!j.role || !j.rationale.trim() || !j.relevance.explanation.trim() ||
          (j.depth && !j.depth.explanation.trim()) || (j.practice && !j.practice.explanation.trim()) ||
          !j.reviewed) { setError('Each book needs a role, explanations and review confirmation.'); return }
      if ((j.role === 'selected_chapters' && !j.focus_topics.length) ||
          j.focus_topics.some(t => !book.topic_keys.includes(t)) ||
          j.evidence_refs.some(ref => !options.has(evidenceKey(ref)))) {
        setError('Correct focus topics and evidence references before saving.'); return
      }
      if (j.evidence_refs.length > 20) { setError('Choose at most 20 evidence references per book.'); return }
    }
    const controller = new AbortController()
    mutation.current = controller
    read.current?.abort()
    setSaving(true); onBusyChange?.(true); setError(''); setNotice('')
    try {
      const result = await putComparison(goal.id, { input_token: editor.token,
        expected_revision: editor.revision, books: editor.books as Judgment[] }, controller.signal)
      if (controller.signal.aborted) return
      setData(result); setEditor(null); setNotice('Comparison saved.'); focusHeading()
    } catch (caught) {
      if (controller.signal.aborted) return
      const e = failure(caught)
      setError(e.message)
      if (['outcome_unknown', 'comparison_inputs_changed', 'comparison_revision_conflict',
        'comparison_not_ready', 'goal_inactive', 'library_storage_unavailable'].includes(e.code)) await load()
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (!controller.signal.aborted) { setSaving(false); onBusyChange?.(false) }
    }
  }
  const display = editor?.preview || data?.saved?.preview || data?.current
  return <section className="book-comparison" aria-labelledby="comparison-heading">
    <h4 id="comparison-heading" ref={heading} tabIndex={-1}>Book comparison</h4>
    <button disabled={disabled || saving || loading} onClick={() => { setError(''); void load() }}>Refresh comparison</button>
    {loading && <p role="status">Loading comparison…</p>}
    {error && <p role="alert">{error}</p>}
    {data && !data.readiness.ready && <div><p>Comparison is not ready.</p><ul>{data.readiness.issues.map((issue, index) =>
      <li key={index}>{issue.message}{issue.book_id && <button disabled={disabled || saving}
        onClick={() => onOpenBook?.(issue.book_id!)}>Open profile for {goal.book_ids.indexOf(issue.book_id) + 1}</button>}</li>)}</ul></div>}
    {data?.stale && <p role="status">Saved comparison is stale. Its captured facts and judgments are shown until you review and save a replacement.</p>}
    {changed && <p role="alert">Inputs or saved results changed. Your draft is preserved. Review with current inputs before saving.</p>}
    {!editor && data?.saved && <p>Saved revision {data.saved.revision}. Facts captured {new Date(data.saved.updated_at).toLocaleString()}.</p>}
    {display && <ComparisonFacts preview={display}
      judgments={editor ? editor.books.filter(book => book.role) as Judgment[] : data?.saved?.books} />}
    {data?.current && (!editor || changed) && <button disabled={disabled || saving || loading} onClick={begin}>
      {data.stale || changed ? 'Review with current inputs' : data.saved ? 'Edit comparison' : 'Classify books'}
    </button>}
    {editor && <form onSubmit={event => void save(event)}>
      <p>Roles are manual judgments: CORE is a primary resource; SELECTED CHAPTERS uses focus topics;
        REFERENCE is for consultation; SKIP FOR NOW defers the book. Exact chapters and order are chosen later.</p>
      <p>Depth: overview introduces ideas; working detail supports practical use; deep treatment develops them extensively.
        Practice is a qualitative learner assessment, separate from profile orientation.</p>
      {editor.books.map(j => {
        const book = editor.preview.books.find(b => b.book_id === j.book_id)!
        const options = evidenceOptions(book, editor.preview)
        const valid = new Set(options.map(o => evidenceKey(o.value)))
        const refs = [...options, ...j.evidence_refs.filter(ref => !valid.has(evidenceKey(ref)))
          .map(value => ({ value, label: 'Unavailable evidence — remove: ' + evidenceKey(value) }))]
        const toggleRef = (ref: Evidence) => change(j.book_id, { reviewed: false, evidence_refs:
          j.evidence_refs.some(r => evidenceKey(r) === evidenceKey(ref))
            ? j.evidence_refs.filter(r => evidenceKey(r) !== evidenceKey(ref)) : [...j.evidence_refs, ref] })
        return <fieldset key={j.book_id} disabled={disabled || saving}>
          <legend>{book.title} — manual judgments</legend>
          <label>Role<select required value={j.role} onChange={e => change(j.book_id, { role: e.target.value as Role, reviewed: false })}>
            <option value="">Choose a role</option>{Object.entries(roleLabels).map(([key, label]) =>
              <option key={key} value={key}>{label}</option>)}</select></label>
          <label>Classification rationale<textarea required maxLength={2000} value={j.rationale}
            onChange={e => change(j.book_id, { rationale: e.target.value, reviewed: false })} /></label>
          <label>Goal relevance<select value={j.relevance.category} onChange={e => change(j.book_id, {
            relevance: { ...j.relevance, category: e.target.value as Judgment['relevance']['category'] }, reviewed: false })}>
            {['high', 'partial', 'low', 'unknown'].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Relevance explanation<textarea required maxLength={1000} value={j.relevance.explanation}
            onChange={e => change(j.book_id, { relevance: { ...j.relevance, explanation: e.target.value }, reviewed: false })} /></label>
          <AssessmentEditor label="Depth" value={j.depth} options={depthLabels}
            onChange={value => change(j.book_id, { depth: value as Judgment['depth'], reviewed: false })} />
          <AssessmentEditor label="Practice content" value={j.practice} options={practiceLabels}
            onChange={value => change(j.book_id, { practice: value as Judgment['practice'], reviewed: false })} />
          <fieldset><legend>Focus topics (required for SELECTED CHAPTERS)</legend>
            {[...new Set([...book.topic_keys, ...j.focus_topics])].map(topic => <label className="comparison-check" key={topic}>
              <input type="checkbox" checked={j.focus_topics.includes(topic)} onChange={() => change(j.book_id, {
                reviewed: false, focus_topics: j.focus_topics.includes(topic) ? j.focus_topics.filter(t => t !== topic) : [...j.focus_topics, topic] })} />
              {topic}{!book.topic_keys.includes(topic) && ' — unavailable; remove'}</label>)}
          </fieldset>
          <details><summary>Optional evidence references ({j.evidence_refs.length}/20)</summary>
            {refs.map(o => <label className="comparison-check" key={evidenceKey(o.value)}>
              <input type="checkbox" checked={j.evidence_refs.some(r => evidenceKey(r) === evidenceKey(o.value))}
                onChange={() => toggleRef(o.value)} />{o.label}</label>)}</details>
          <label className="comparison-check"><input type="checkbox" checked={j.reviewed}
            onChange={e => change(j.book_id, { reviewed: e.target.checked })} />I reviewed this book against the current comparison inputs.</label>
        </fieldset>
      })}
      <button type="button" disabled={saving} onClick={() => { setEditor(null); setError(''); focusHeading() }}>Cancel comparison edit</button>
      <button type="submit" disabled={disabled || saving || changed || loading}>{saving ? 'Saving comparison…' : 'Save comparison'}</button>
    </form>}
    <p role="status" aria-label="Comparison activity">{saving ? 'Saving comparison…' : notice}</p>
  </section>
}
