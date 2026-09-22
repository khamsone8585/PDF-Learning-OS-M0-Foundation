import { useCallback, useEffect, useRef, useState } from 'react'
import { getBook, getChapters, LibraryError, processBook, updateChapters } from '../../api/books'
import type { Book, ChaptersResponse } from '../../api/books'

interface Props {
  book: Book
  disabled: boolean
  onBookChange: (book: Book) => void
  onBusyChange: (busy: boolean) => void
}

const asError = (error: unknown) => error instanceof LibraryError ? error : new LibraryError('Processing request failed.')
const labels = { unprocessed: 'Not processed', processing: 'Processing…', processed: 'Processed', failed: 'Processing failed' }
const sourceLabels = { toc: 'PDF bookmarks', fallback: 'Fallback structure', manual: 'Manually corrected structure' }

export default function ProcessingPanel({ book, disabled, onBookChange, onBusyChange }: Props) {
  const [outline, setOutline] = useState<ChaptersResponse | null>(null)
  const [outlineError, setOutlineError] = useState('')
  const [actionError, setActionError] = useState<LibraryError | null>(null)
  const [notice, setNotice] = useState('')
  const [working, setWorking] = useState<'process' | 'correct' | null>(null)
  const [editing, setEditing] = useState(false)
  const [sections, setSections] = useState<Array<{ title: string; start_page: number }>>([])
  const read = useRef<AbortController | null>(null)
  const mutation = useRef<AbortController | null>(null)

  const loadOutline = useCallback(async () => {
    read.current?.abort()
    const controller = new AbortController()
    read.current = controller
    setOutlineError('')
    try {
      setOutline(await getChapters(book.id, controller.signal))
    } catch (error) {
      if (!controller.signal.aborted) setOutlineError(asError(error).message)
    }
  }, [book.id])

  useEffect(() => {
    void loadOutline()
    return () => read.current?.abort()
  }, [loadOutline, book.processing_status, book.has_processed_content])

  useEffect(() => {
    if (book.processing_status !== 'processing') return
    const interval = setInterval(async () => {
      try {
        const latest = await getBook(book.id)
        onBookChange(latest)
      } catch {
        // The active processing request and visible status remain authoritative.
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [book.id, book.processing_status, onBookChange])

  useEffect(() => () => mutation.current?.abort(), [])

  async function runProcessing() {
    if (mutation.current) return
    const controller = new AbortController()
    mutation.current = controller
    setWorking('process'); onBusyChange(true); setActionError(null); setNotice('')
    try {
      const result = await processBook(book.id, controller.signal)
      if (controller.signal.aborted) return
      onBookChange(result)
      setNotice(`Processed ${book.title}.`)
      await loadOutline()
    } catch (error) {
      if (controller.signal.aborted) return
      const failure = asError(error)
      setActionError(failure)
      try { onBookChange(await getBook(book.id)) } catch { /* Keep the known state. */ }
      await loadOutline()
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (!controller.signal.aborted) { setWorking(null); onBusyChange(false) }
    }
  }

  function beginEditing() {
    if (!outline) return
    setSections(outline.chapters.map(chapter => ({ title: chapter.title, start_page: chapter.start_page })))
    setActionError(null); setEditing(true)
  }

  async function saveSections() {
    if (mutation.current) return
    const controller = new AbortController()
    mutation.current = controller
    setWorking('correct'); onBusyChange(true); setActionError(null); setNotice('')
    try {
      const result = await updateChapters(book.id, sections, controller.signal)
      if (controller.signal.aborted) return
      setOutline(result); setEditing(false); setNotice('Section structure saved.')
    } catch (error) {
      if (!controller.signal.aborted) setActionError(asError(error))
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (!controller.signal.aborted) { setWorking(null); onBusyChange(false) }
    }
  }

  const serverError = actionError || (book.processing_error
    ? new LibraryError(book.processing_error.message, book.processing_error.code) : null)
  const processing = working === 'process' || book.processing_status === 'processing'
  const canEdit = outline && book.processing_status === 'processed' &&
    ['fallback', 'manual'].includes(outline.structure_source || '')

  return <section className="processing-panel" aria-labelledby="processing-heading">
    <h4 id="processing-heading">PDF processing</h4>
    <p>Status: <strong>{labels[book.processing_status]}</strong></p>
    {book.has_processed_content && book.processing_status === 'failed' &&
      <p>The previous successful extraction is still available.</p>}
    {serverError && <div role="alert">
      <p>{serverError.message}</p>
      {serverError.code === 'ocr_required' &&
        <p>This document appears image-only or has too little machine-readable text. OCR is not supported in V0.1.</p>}
    </div>}
    <p role="status" aria-label="Processing activity">{processing ? 'Processing PDF…' : notice}</p>
    <button disabled={disabled || processing || !book.file_available} onClick={() => void runProcessing()}>
      {processing ? 'Processing…' : book.processed_at || book.processing_status === 'failed' ? 'Reprocess PDF' : 'Process PDF'}
    </button>

    <h4>Chapter structure</h4>
    {outlineError && <div role="alert"><p>{outlineError}</p><button onClick={() => void loadOutline()}>Retry chapters</button></div>}
    {outline?.structure_source && <p>{sourceLabels[outline.structure_source]}
      {outline.toc_status === 'partial' ? ' (some invalid bookmarks were skipped)' : ''}</p>}
    {outline && outline.chapters.length === 0 && <p>No chapter structure yet. Process the PDF to create one.</p>}
    {outline && outline.chapters.length > 0 && !editing && <ol className="chapter-list">
      {outline.chapters.map(chapter => <li key={chapter.id} style={{ marginLeft: `${(chapter.level - 1) * 1.25}rem` }}>
        <span>{chapter.title}</span><span>Pages {chapter.start_page}–{chapter.end_page}</span>
      </li>)}
    </ol>}
    {canEdit && !editing && <button disabled={disabled || processing} onClick={beginEditing}>Correct fallback sections</button>}
    {editing && <div className="chapter-editor" aria-label="Correct fallback sections">
      {sections.map((section, index) => <fieldset key={index} disabled={working !== null}>
        <legend>Section {index + 1}</legend>
        <label>Section title<input value={section.title} maxLength={500}
          onChange={event => setSections(values => values.map((value, item) => item === index
            ? { ...value, title: event.target.value } : value))} /></label>
        <label>Start page<input type="number" min={1} max={book.page_count} value={section.start_page}
          onChange={event => setSections(values => values.map((value, item) => item === index
            ? { ...value, start_page: Number(event.target.value) } : value))} /></label>
        {sections.length > 1 && <button onClick={() => setSections(values => values.filter((_value, item) => item !== index))}>Remove section {index + 1}</button>}
      </fieldset>)}
      <button disabled={working !== null} onClick={() => setSections(values => [...values,
        { title: '', start_page: Math.min(book.page_count, (values.at(-1)?.start_page || 0) + 1) }])}>Add section</button>
      <button disabled={working !== null} onClick={() => { setEditing(false); setActionError(null) }}>Cancel correction</button>
      <button disabled={working !== null} onClick={() => void saveSections()}>{working === 'correct' ? 'Saving…' : 'Save sections'}</button>
    </div>}
  </section>
}
