import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { LibraryError } from '../../api/books'
import type { Book } from '../../api/books'
import type { Judgment, Role } from '../../api/bookComparisons'
import { createTriage, confirmTriage, getLibraryMap, getPrerequisites, getRelations,
  getTriage, listTriages, putRelationReview, updateTriage } from '../../api/libraryIntelligence'
import type { LibraryMap, MapBook, Prerequisite, Relation, TriageEnvelope,
  TriageFields, TriageSession } from '../../api/libraryIntelligence'

interface Props {
  books: Book[]; disabled: boolean; refreshKey?: number
  onOpenBook: (id: string) => void; onBusyChange: (busy: boolean) => void; onApplied: () => void
}
type Draft = Omit<Judgment, 'role'> & { role: Role | '' }
const failure = (error: unknown) => error instanceof LibraryError ? error : new LibraryError('Library intelligence request failed.')
const split = (value: string) => value.split('\n').map(item => item.trim()).filter(Boolean)
const profileEvidenceFields = ['domain', 'difficulty', 'prerequisites', 'main_topics', 'orientation',
  'strengths', 'weaknesses', 'suggested_use'] as const
const empty = (id: string): Draft => ({ book_id: id, role: '', rationale: '',
  relevance: { category: 'unknown', explanation: '' }, depth: null, practice: null,
  focus_topics: [], evidence_refs: [], reviewed: false })

export default function LibraryIntelligence({ books, disabled, refreshKey = 0,
  onOpenBook, onBusyChange, onApplied }: Props) {
  const [open, setOpen] = useState(false)
  const [map, setMap] = useState<LibraryMap | null>(null)
  const [bibliographic, setBibliographic] = useState<Relation[]>([])
  const [bibliographicTotal, setBibliographicTotal] = useState(0)
  const [overlaps, setOverlaps] = useState<Relation[]>([])
  const [overlapTotal, setOverlapTotal] = useState(0)
  const [prerequisites, setPrerequisites] = useState<Prerequisite[]>([])
  const [prerequisiteTotal, setPrerequisiteTotal] = useState(0)
  const [history, setHistory] = useState<TriageSession[]>([])
  const [triage, setTriage] = useState<TriageEnvelope | null>(null)
  const [historyView, setHistoryView] = useState<TriageEnvelope | null>(null)
  const [archiveDraftId, setArchiveDraftId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [readiness, setReadiness] = useState('all')
  const [domainFilter, setDomainFilter] = useState('all')
  const [topicFilter, setTopicFilter] = useState('all')
  const [difficultyFilter, setDifficultyFilter] = useState('all')
  const [orientationFilter, setOrientationFilter] = useState('all')
  const [processingFilter, setProcessingFilter] = useState('all')
  const [candidateFilter, setCandidateFilter] = useState('all')
  const [group, setGroup] = useState<'domain' | 'topic' | 'readiness'>('domain')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [targetTopics, setTargetTopics] = useState('')
  const [targetDomain, setTargetDomain] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [scopeKind, setScopeKind] = useState<'library_snapshot' | 'selected'>('library_snapshot')
  const [candidateIds, setCandidateIds] = useState<string[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [judgments, setJudgments] = useState<Draft[]>([])
  const [reviewedRecommendation, setReviewedRecommendation] = useState(false)
  const controller = useRef<AbortController | null>(null)
  const mutation = useRef<AbortController | null>(null)
  const queuedProfile = useRef<string | null>(null)
  const priorProfileRefresh = useRef(refreshKey)
  const heading = useRef<HTMLHeadingElement>(null)

  const adopt = useCallback((value: TriageEnvelope) => {
    setTriage(value); setTitle(value.session.title); setDescription(value.session.description || '')
    setTargetTopics(value.session.target_topics.join('\n')); setTargetDomain(value.session.target_domain || '')
    setDifficulty(value.session.difficulty_ceiling || ''); setScopeKind(value.session.scope_kind)
    setCandidateIds(value.session.book_ids)
    const suggested = value.recommendation.suggested_book_ids
    setSelected(suggested); setJudgments(suggested.map(empty)); setReviewedRecommendation(false)
  }, [])

  const load = useCallback(async () => {
    controller.current?.abort()
    const current = new AbortController(); controller.current = current
    setLoading(true); setError('')
    try {
      const [libraryMap, bibliography, topicRelations, prerequisitePage, sessions] = await Promise.all([
        getLibraryMap(current.signal), getRelations('bibliographic', current.signal),
        getRelations('topic_overlap', current.signal), getPrerequisites(current.signal), listTriages(current.signal),
      ])
      if (current.signal.aborted) return
      setMap(libraryMap); setBibliographic(bibliography.items); setOverlaps(topicRelations.items)
      setBibliographicTotal(bibliography.total); setOverlapTotal(topicRelations.total)
      setPrerequisites(prerequisitePage.items); setPrerequisiteTotal(prerequisitePage.total); setHistory(sessions)
      const draft = sessions.find(item => item.status === 'draft')
      if (draft) adopt(await getTriage(draft.id, current.signal))
      else setTriage(null)
    } catch (caught) {
      if (!current.signal.aborted) setError(failure(caught).message)
    } finally { if (!current.signal.aborted) setLoading(false) }
  }, [adopt])

  useEffect(() => () => { controller.current?.abort(); mutation.current?.abort() }, [])
  useEffect(() => { if (open) void load() }, [open, load, books.length, refreshKey])
  useEffect(() => {
    if (refreshKey === priorProfileRefresh.current) return
    priorProfileRefresh.current = refreshKey
    if (!map || !queuedProfile.current) return
    const incomplete = map.books.filter(book => book.readiness !== 'triage_ready')
    const current = incomplete.findIndex(book => book.book_id === queuedProfile.current)
    const next = incomplete[current >= 0 ? current + 1 : 0]
    queuedProfile.current = next?.book_id || null
    if (next) onOpenBook(next.book_id)
  }, [map, onOpenBook, refreshKey])

  const visible = useMemo(() => (map?.books || []).filter(book =>
    (readiness === 'all' || book.readiness === readiness) &&
    (domainFilter === 'all' || (book.domain_key || 'unknown') === domainFilter) &&
    (topicFilter === 'all' || book.topic_keys.includes(topicFilter)) &&
    (difficultyFilter === 'all' || (book.profile?.difficulty || 'unknown') === difficultyFilter) &&
    (orientationFilter === 'all' || (book.profile?.orientation || 'unknown') === orientationFilter) &&
    (processingFilter === 'all' || book.processing_status === processingFilter) &&
    (candidateFilter === 'all' || (triage?.session.book_ids.includes(book.book_id) === (candidateFilter === 'candidate'))) &&
    [book.title, book.author || '', book.domain_key || '', ...book.topic_keys]
      .some(value => value.toLocaleLowerCase().includes(search.toLocaleLowerCase()))),
  [candidateFilter, difficultyFilter, domainFilter, map, orientationFilter, processingFilter,
    readiness, search, topicFilter, triage])
  const grouped = useMemo(() => {
    const result = new Map<string, MapBook[]>()
    for (const book of visible) {
      const key = group === 'readiness' ? book.readiness : group === 'topic' ? book.topic_keys[0] || 'unknown'
        : book.domain_key || 'unknown'
      result.set(key, [...(result.get(key) || []), book])
    }
    return [...result.entries()].sort(([left], [right]) => left.localeCompare(right))
  }, [visible, group])

  async function mutate(action: (signal: AbortSignal) => Promise<unknown>, success: string,
                        preserveEditorOnUnknown = false) {
    if (working) return
    const current = new AbortController(); mutation.current = current
    const editor = { title, description, targetTopics, targetDomain, difficulty, scopeKind,
      candidateIds, selected, judgments, reviewedRecommendation }
    setWorking(true); onBusyChange(true); setError(''); setNotice('')
    try {
      await action(current.signal)
      if (!current.signal.aborted) { setNotice(success); await load(); setTimeout(() => heading.current?.focus(), 0) }
    } catch (caught) {
      if (!current.signal.aborted) {
        const problem = failure(caught)
        if (problem.code === 'outcome_unknown') {
          await load()
          if (preserveEditorOnUnknown) {
            setTitle(editor.title); setDescription(editor.description); setTargetTopics(editor.targetTopics)
            setTargetDomain(editor.targetDomain); setDifficulty(editor.difficulty); setScopeKind(editor.scopeKind)
            setCandidateIds(editor.candidateIds); setSelected(editor.selected); setJudgments(editor.judgments)
            setReviewedRecommendation(editor.reviewedRecommendation)
          }
        }
        setError(problem.message)
      }
    } finally {
      if (mutation.current === current) mutation.current = null
      if (!current.signal.aborted) { setWorking(false); onBusyChange(false) }
    }
  }

  function fields(): TriageFields {
    return { title, description: description.trim() || null, target_topics: split(targetTopics),
      target_domain: targetDomain.trim() || null, difficulty_ceiling: difficulty ? difficulty as TriageFields['difficulty_ceiling'] : null,
      scope: { kind: scopeKind, book_ids: scopeKind === 'selected' ? candidateIds : [] } }
  }
  async function saveSession(event: FormEvent) {
    event.preventDefault()
    if (!title.trim() || split(targetTopics).length < 1) { setError('Enter a title and at least one target topic.'); return }
    await mutate(async signal => {
      const result = triage
        ? await updateTriage(triage.session.id, { ...fields(), input_token: triage.input_token,
          expected_revision: triage.session.revision }, signal)
        : await createTriage({ ...fields(), archive_draft_id: archiveDraftId }, signal)
      setArchiveDraftId(null); adopt(result)
    }, triage ? 'Triage synchronized and saved.' : 'Curriculum triage created.', true)
  }

  function toggleSelected(id: string) {
    setSelected(current => current.includes(id) ? current.filter(item => item !== id)
      : current.length < 5 ? [...current, id] : current)
    setJudgments(current => current.some(item => item.book_id === id)
      ? current.filter(item => item.book_id !== id) : [...current, empty(id)])
    setReviewedRecommendation(false)
  }
  function changeJudgment(id: string, values: Partial<Draft>) {
    setJudgments(current => current.map(item => item.book_id === id
      ? { ...item, ...values, reviewed: values.reviewed ?? false } : item))
  }
  async function confirm(event: FormEvent) {
    event.preventDefault()
    if (!triage || selected.length < 3 || selected.length > 5 || !reviewedRecommendation) {
      setError('Select 3–5 books and confirm that you reviewed the recommendation.'); return
    }
    const chosen = selected.map(id => judgments.find(item => item.book_id === id) || empty(id))
    if (chosen.some(item => !item.role || !item.rationale.trim() || !item.relevance.explanation.trim() || !item.reviewed ||
      (item.depth !== null && !item.depth.explanation.trim()) ||
      (item.practice !== null && !item.practice.explanation.trim()) ||
      (item.role === 'selected_chapters' && !item.focus_topics.length))) {
      setError('Every selected book needs a valid role, rationale, relevance explanation, optional assessment explanations, focus topics when selected, and review confirmation.'); return
    }
    if (!chosen.some(item => item.role === 'core' || item.role === 'selected_chapters')) {
      setError('Choose at least one CORE or SELECTED book for Books Now.'); return
    }
    await mutate(async signal => {
      await confirmTriage(triage.session.id, { input_token: triage.input_token,
        expected_revision: triage.session.revision, reviewed_recommendation: true,
        books: chosen as Judgment[] }, signal)
      onApplied()
    }, 'Books Now confirmed as the new active learning goal.', true)
  }

  async function review(relation: Relation, decision: 'same_work' | 'related_edition' | 'distinct', preferred: string | null) {
    await mutate(signal => putRelationReview({ left_book_id: relation.left_book_id,
      right_book_id: relation.right_book_id, decision, preferred_book_id: preferred, note: null }, signal),
    'Bibliographic relation reviewed.')
  }

  async function loadMore(kind: 'bibliographic' | 'overlap' | 'prerequisite') {
    if (loading || working) return
    const current = new AbortController(); controller.current = current
    setLoading(true); setError('')
    try {
      if (kind === 'bibliographic') {
        const page = await getRelations('bibliographic', current.signal, bibliographic.length)
        if (!current.signal.aborted) { setBibliographic(items => [...items, ...page.items]); setBibliographicTotal(page.total) }
      } else if (kind === 'overlap') {
        const page = await getRelations('topic_overlap', current.signal, overlaps.length)
        if (!current.signal.aborted) { setOverlaps(items => [...items, ...page.items]); setOverlapTotal(page.total) }
      } else {
        const page = await getPrerequisites(current.signal, prerequisites.length)
        if (!current.signal.aborted) { setPrerequisites(items => [...items, ...page.items]); setPrerequisiteTotal(page.total) }
      }
    } catch (caught) {
      if (!current.signal.aborted) setError(failure(caught).message)
    } finally { if (!current.signal.aborted) setLoading(false) }
  }

  async function viewHistory(id: string) {
    if (loading || working) return
    const current = new AbortController(); controller.current = current
    setLoading(true); setError('')
    try {
      const value = await getTriage(id, current.signal)
      if (!current.signal.aborted) setHistoryView(value)
    } catch (caught) {
      if (!current.signal.aborted) setError(failure(caught).message)
    } finally { if (!current.signal.aborted) setLoading(false) }
  }

  if (!open) return <section className="library-intelligence" aria-labelledby="intelligence-closed-heading">
    <h3 id="intelligence-closed-heading">Library intelligence</h3>
    <p>Map, review, and triage a large candidate library from recorded metadata and profiles.</p>
    <button disabled={disabled} onClick={() => setOpen(true)}>Open library intelligence</button>
  </section>

  return <section className="library-intelligence" aria-labelledby="intelligence-heading">
    <h3 id="intelligence-heading" ref={heading} tabIndex={-1}>Library intelligence</h3>
    <p>Exact recorded metadata and profile matches only. No PDF text, semantic matching, score, or study order is used.</p>
    <button disabled={disabled || loading || working} onClick={() => void load()}>Refresh intelligence</button>
    <button disabled={working} onClick={() => setOpen(false)}>Close intelligence</button>
    {loading && <p role="status">Loading library intelligence…</p>}
    {error && <p role="alert">{error}</p>}
    {map && <>
      <h4>Library map</h4>
      <p>{map.counts.books} books · {map.counts.triage_ready || 0} triage ready · {map.counts.profile_missing || 0} missing profiles · {map.counts.topics_missing || 0} missing topics</p>
      <div className="intelligence-filters">
        <label>Search books<input value={search} onChange={event => setSearch(event.target.value)} /></label>
        <label>Readiness<select value={readiness} onChange={event => setReadiness(event.target.value)}>
          <option value="all">All</option><option value="triage_ready">Triage ready</option>
          <option value="profile_missing">Profile missing</option><option value="topics_missing">Topics missing</option>
        </select></label>
        <label>Group by<select value={group} onChange={event => setGroup(event.target.value as typeof group)}>
          <option value="domain">Domain</option><option value="topic">First topic</option><option value="readiness">Readiness</option>
        </select></label>
        <label>Domain<select value={domainFilter} onChange={event => setDomainFilter(event.target.value)}>
          <option value="all">All domains</option>{map.groups.domains.map(item =>
            <option key={item.key} value={item.key}>{item.label} ({item.count})</option>)}</select></label>
        <label>Topic<select value={topicFilter} onChange={event => setTopicFilter(event.target.value)}>
          <option value="all">All topics</option>{map.groups.topics.map(item =>
            <option key={item.key} value={item.key}>{item.label} ({item.count})</option>)}</select></label>
        <label>Difficulty<select value={difficultyFilter} onChange={event => setDifficultyFilter(event.target.value)}>
          <option value="all">All difficulties</option><option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
          <option value="unknown">Unknown</option></select></label>
        <label>Orientation<select value={orientationFilter} onChange={event => setOrientationFilter(event.target.value)}>
          <option value="all">All orientations</option><option value="theory_heavy">Theory-heavy</option>
          <option value="balanced">Balanced</option><option value="practice_heavy">Practice-heavy</option>
          <option value="unknown">Unknown</option></select></label>
        <label>Processing<select value={processingFilter} onChange={event => setProcessingFilter(event.target.value)}>
          <option value="all">All processing states</option><option value="unprocessed">Unprocessed</option>
          <option value="processing">Processing</option><option value="processed">Processed</option>
          <option value="failed">Failed</option></select></label>
        <label>Candidate membership<select value={candidateFilter} onChange={event => setCandidateFilter(event.target.value)}>
          <option value="all">All books</option><option value="candidate">Current candidates</option>
          <option value="not_candidate">Not current candidates</option></select></label>
      </div>
      {grouped.map(([key, items]) => <details key={key} open><summary>{key} ({items.length})</summary>
        <ul className="intelligence-books">{items.map(book => <li key={book.book_id}>
          <button disabled={disabled || working} onClick={() => onOpenBook(book.book_id)}>{book.title}</button>
          <span>{book.readiness.replaceAll('_', ' ')} · {book.profile?.difficulty || 'difficulty unknown'} · {book.profile?.orientation || 'orientation unknown'}</span>
          <span>Topics: {book.profile?.main_topics.join(', ') || 'not recorded'}</span>
          <span>{book.bibliographic_relation_count} bibliographic · {book.topic_relation_count} overlap · {book.unique_topic_count} unique topics · {book.prerequisite_count} prerequisites</span>
        </li>)}</ul></details>)}

      <h4>Profile readiness</h4>
      {!map.books.some(book => book.readiness !== 'triage_ready') ? <p>Every book is triage ready.</p> : <>
        <p>Complete profiles and record at least one main topic. Saving advances an active queue to the next incomplete book.</p>
        <button disabled={disabled || working} onClick={() => {
          const first = map.books.find(book => book.readiness !== 'triage_ready')
          if (first) { queuedProfile.current = first.book_id; onOpenBook(first.book_id) }
        }}>Open next incomplete profile</button>
        <ul>{map.books.filter(book => book.readiness !== 'triage_ready').map(book => <li key={book.book_id}>
          <button disabled={disabled || working} onClick={() => {
            queuedProfile.current = book.book_id; onOpenBook(book.book_id)
          }}>{book.title}</button> — {book.readiness.replaceAll('_', ' ')}
        </li>)}</ul>
      </>}

      <h4>Duplicates and related editions</h4>
      {!bibliographic.length && <p>No exact normalized title-and-author candidates.</p>}
      {bibliographic.map(item => <article className="relation-card" key={`${item.left_book_id}:${item.right_book_id}`}>
        <p><strong>{map.books.find(book => book.book_id === item.left_book_id)?.title}</strong> / <strong>{map.books.find(book => book.book_id === item.right_book_id)?.title}</strong></p>
        <p>{item.classification.replaceAll('_', ' ')} · derived from exact normalized title and author. {item.review && `Reviewed: ${item.review.decision.replaceAll('_', ' ')}.`}</p>
        <button disabled={working} onClick={() => void review(item, 'related_edition', null)}>Related editions</button>
        <button disabled={working} onClick={() => void review(item, 'distinct', null)}>Distinct books</button>
        <button disabled={working} onClick={() => void review(item, 'same_work', item.left_book_id)}>Same work; prefer first</button>
        <button disabled={working} onClick={() => void review(item, 'same_work', item.right_book_id)}>Same work; prefer second</button>
      </article>)}
      {bibliographic.length < bibliographicTotal && <button disabled={loading || working}
        onClick={() => void loadMore('bibliographic')}>Load more duplicate candidates</button>}

      <details><summary>Recorded-topic overlap ({overlaps.length})</summary>
        <ul>{overlaps.map(item => <li key={`${item.left_book_id}:${item.right_book_id}`}>
          {map.books.find(book => book.book_id === item.left_book_id)?.title} / {map.books.find(book => book.book_id === item.right_book_id)?.title}: {item.classification.replaceAll('_', ' ')}.
          Shared: {(item.shared_topics || []).join(', ') || 'none'}; first only: {(item.left_only || []).join(', ') || 'none'};
          second only: {(item.right_only || []).join(', ') || 'none'}; {item.complementary ? 'complementary recorded topics' : 'no recorded complement'}.
        </li>)}</ul>{overlaps.length < overlapTotal && <button disabled={loading || working}
          onClick={() => void loadMore('overlap')}>Load more topic relationships</button>}</details>
      <details><summary>Explicit prerequisites ({prerequisites.length})</summary>
        <ul>{prerequisites.map(item => <li key={`${item.book_id}:${item.normalized_key}`}>
          {map.books.find(book => book.book_id === item.book_id)?.title}: {item.prerequisite} ({item.profile_source}) — {item.unresolved ? 'unresolved' : `provided by ${item.providers.map(provider => `${map.books.find(book => book.book_id === provider.book_id)?.title} ${provider.field.replaceAll('_', ' ')}`).join(', ')}`}
        </li>)}</ul>{prerequisites.length < prerequisiteTotal && <button disabled={loading || working}
          onClick={() => void loadMore('prerequisite')}>Load more prerequisites</button>}</details>

      <h4>Curriculum triage</h4>
      {triage && <button disabled={disabled || working} onClick={() => {
        setArchiveDraftId(triage.session.id); setTriage(null); setTitle(''); setDescription('')
        setTargetTopics(''); setTargetDomain(''); setDifficulty(''); setScopeKind('library_snapshot')
        setCandidateIds([]); setSelected([]); setJudgments([]); setReviewedRecommendation(false)
      }}>Start a replacement draft</button>}
      {archiveDraftId && <p role="status">Saving this replacement will atomically archive the existing draft.
        <button disabled={working} onClick={() => { setArchiveDraftId(null); void load() }}>Cancel replacement</button></p>}
      <form onSubmit={event => void saveSession(event)}>
        <fieldset disabled={disabled || working}>
          <legend>{triage ? 'Edit and synchronize draft' : 'Create a curriculum triage'}</legend>
          <label>Learning intent title<input required maxLength={200} value={title} onChange={event => setTitle(event.target.value)} /></label>
          <label>Description (optional)<textarea maxLength={2000} value={description} onChange={event => setDescription(event.target.value)} /></label>
          <label>Target topics (one per line)<textarea required value={targetTopics} onChange={event => setTargetTopics(event.target.value)} /></label>
          <label>Target domain (optional)<input maxLength={200} value={targetDomain} onChange={event => setTargetDomain(event.target.value)} /></label>
          <label>Difficulty ceiling (optional)<select value={difficulty} onChange={event => setDifficulty(event.target.value)}>
            <option value="">No ceiling</option><option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
          </select></label>
          <label>Candidate scope<select value={scopeKind} onChange={event => setScopeKind(event.target.value as typeof scopeKind)}>
            <option value="library_snapshot">Current whole-library snapshot</option><option value="selected">Selected candidates</option>
          </select></label>
          {scopeKind === 'selected' && <fieldset><legend>Candidate books ({candidateIds.length})</legend>
            {map.books.map(book => <label className="intelligence-check" key={book.book_id}><input type="checkbox"
              checked={candidateIds.includes(book.book_id)} onChange={() => setCandidateIds(current => current.includes(book.book_id)
                ? current.filter(id => id !== book.book_id) : [...current, book.book_id])} />{book.title}</label>)}
          </fieldset>}
          <button type="submit">{working ? 'Saving…' : triage ? 'Save and synchronize triage' : 'Create triage'}</button>
        </fieldset>
      </form>
      {triage && <>
        {triage.stale && <p role="alert">Triage inputs are stale: {triage.stale_reasons.join(', ')}. Save and synchronize before confirmation.</p>}
        <p>{triage.readiness.ready_count}/{triage.readiness.candidate_count} candidates are ready.</p>
        {triage.recommendation.issues.map((issue, index) => <p key={index} role="status">{String(issue.message || issue.code)}</p>)}
        <form onSubmit={event => void confirm(event)}>
          <fieldset disabled={disabled || working || triage.stale}>
            <legend>Confirm 3–5 Books Now ({selected.length} selected)</legend>
            <p>CORE, SELECTED, and REFERENCE books are included in Books Now. Unselected candidates are LATER and remain outside the active study set.</p>
            {triage.recommendation.books.map(item => {
              const checked = selected.includes(item.book_id)
              const candidate = triage.candidates.find(value => value.book_id === item.book_id)!
              return <div className="triage-book" key={item.book_id}>
                <label className="intelligence-check"><input type="checkbox" checked={checked}
                  disabled={candidate.readiness !== 'triage_ready' || (!checked && selected.length >= 5)}
                  onChange={() => toggleSelected(item.book_id)} />
                  {item.title} — {item.band.replaceAll('_', ' ')}{item.above_ceiling ? ' — above ceiling' : ''}</label>
                <p>Target matches: {item.matched_target_topics.join(', ') || 'none'}; prerequisite matches: {item.matched_prerequisites.join(', ') || 'none'}; unique topics: {item.unique_topics.join(', ') || 'none'}.</p>
                {checked && (() => {
                  const judgment = judgments.find(value => value.book_id === item.book_id) || empty(item.book_id)
                  return <fieldset><legend>{item.title} manual decision</legend>
                    <label>Role<select required value={judgment.role} onChange={event => changeJudgment(item.book_id, { role: event.target.value as Role })}>
                      <option value="">Choose</option><option value="core">CORE</option>
                      <option value="selected_chapters">SELECTED</option><option value="reference">REFERENCE</option>
                    </select></label>
                    <label>Rationale<textarea required maxLength={2000} value={judgment.rationale} onChange={event => changeJudgment(item.book_id, { rationale: event.target.value })} /></label>
                    <label>Relevance<select value={judgment.relevance.category} onChange={event => changeJudgment(item.book_id, { relevance: { ...judgment.relevance, category: event.target.value as Judgment['relevance']['category'] } })}>
                      {['high', 'partial', 'low', 'unknown'].map(value => <option value={value} key={value}>{value}</option>)}</select></label>
                    <label>Relevance explanation<textarea required maxLength={1000} value={judgment.relevance.explanation}
                      onChange={event => changeJudgment(item.book_id, { relevance: { ...judgment.relevance, explanation: event.target.value } })} /></label>
                    <label>Depth assessment (optional)<select value={judgment.depth?.category || ''}
                      onChange={event => changeJudgment(item.book_id, { depth: event.target.value
                        ? { category: event.target.value as NonNullable<Judgment['depth']>['category'], explanation: '' } : null })}>
                      <option value="">Unknown</option><option value="overview">Overview</option>
                      <option value="working_detail">Working detail</option><option value="deep_treatment">Deep treatment</option>
                    </select></label>
                    {judgment.depth && <label>Depth explanation<textarea required maxLength={1000} value={judgment.depth.explanation}
                      onChange={event => changeJudgment(item.book_id, { depth: { ...judgment.depth!, explanation: event.target.value } })} /></label>}
                    <label>Practice assessment (optional)<select value={judgment.practice?.category || ''}
                      onChange={event => changeJudgment(item.book_id, { practice: event.target.value
                        ? { category: event.target.value as NonNullable<Judgment['practice']>['category'], explanation: '' } : null })}>
                      <option value="">Unknown</option><option value="limited">Limited</option>
                      <option value="some">Some</option><option value="substantial">Substantial</option>
                    </select></label>
                    {judgment.practice && <label>Practice explanation<textarea required maxLength={1000} value={judgment.practice.explanation}
                      onChange={event => changeJudgment(item.book_id, { practice: { ...judgment.practice!, explanation: event.target.value } })} /></label>}
                    <fieldset><legend>Focus topics (required for SELECTED)</legend>{candidate.topic_keys.map(topic =>
                      <label className="intelligence-check" key={topic}><input type="checkbox" checked={judgment.focus_topics.includes(topic)}
                        onChange={() => changeJudgment(item.book_id, { focus_topics: judgment.focus_topics.includes(topic)
                          ? judgment.focus_topics.filter(value => value !== topic) : [...judgment.focus_topics, topic] })} />{topic}</label>)}</fieldset>
                    <fieldset><legend>Optional topic evidence</legend>{candidate.topic_keys.map(topic =>
                      <label className="intelligence-check" key={topic}><input type="checkbox"
                        checked={judgment.evidence_refs.some(ref => ref.kind === 'topic' && ref.topic === topic)}
                        onChange={() => changeJudgment(item.book_id, { evidence_refs: judgment.evidence_refs.some(ref => ref.kind === 'topic' && ref.topic === topic)
                          ? judgment.evidence_refs.filter(ref => !(ref.kind === 'topic' && ref.topic === topic))
                          : [...judgment.evidence_refs, { kind: 'topic', topic }] })} />{topic}</label>)}</fieldset>
                    {candidate.profile && <fieldset><legend>Optional profile-field evidence</legend>
                      {profileEvidenceFields.filter(field => {
                        const value = candidate.profile![field]
                        return Array.isArray(value) ? value.length > 0 : !!value
                      }).map(field => <label className="intelligence-check" key={field}><input type="checkbox"
                        checked={judgment.evidence_refs.some(ref => ref.kind === 'profile_field' && ref.field === field)}
                        onChange={() => changeJudgment(item.book_id, { evidence_refs: judgment.evidence_refs.some(ref => ref.kind === 'profile_field' && ref.field === field)
                          ? judgment.evidence_refs.filter(ref => !(ref.kind === 'profile_field' && ref.field === field))
                          : [...judgment.evidence_refs, { kind: 'profile_field', field }] })} />{field.replaceAll('_', ' ')}</label>)}
                    </fieldset>}
                    <label className="intelligence-check"><input type="checkbox" checked={judgment.reviewed}
                      onChange={event => changeJudgment(item.book_id, { reviewed: event.target.checked })} />I reviewed this book against the current inputs.</label>
                  </fieldset>
                })()}
              </div>
            })}
            <label className="intelligence-check"><input type="checkbox" checked={reviewedRecommendation}
              onChange={event => setReviewedRecommendation(event.target.checked)} />I reviewed the deterministic recommendation, warnings, and any manual overrides.</label>
            <p>Confirmation creates a new active goal and deactivates the current one.</p>
            <button type="submit">{working ? 'Confirming…' : 'Confirm Books Now'}</button>
          </fieldset>
        </form>
      </>}
      {!!history.filter(item => item.status !== 'draft').length && <details><summary>Triage history</summary><ul>
        {history.filter(item => item.status !== 'draft').map(item => <li key={item.id}>{item.title} — {item.status}
          <button disabled={loading || working} onClick={() => void viewHistory(item.id)}>View</button></li>)}
      </ul></details>}
      {historyView && <section aria-labelledby="triage-history-heading">
        <h4 id="triage-history-heading">{historyView.session.title} — {historyView.session.status}</h4>
        <p>{historyView.session.description || 'No description.'}</p>
        <p>Targets: {historyView.session.target_topics.join(', ')}. Candidates: {historyView.session.book_ids.length}.</p>
        <p>Saved history is read-only. {historyView.stale && `Current inputs differ: ${historyView.stale_reasons.join(', ')}.`}</p>
        <button onClick={() => setHistoryView(null)}>Close history</button>
      </section>}
    </>}
    <p role="status" aria-label="Library intelligence activity">{working ? 'Saving library intelligence…' : notice}</p>
  </section>
}
