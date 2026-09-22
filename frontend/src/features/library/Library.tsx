import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { deleteBook, getBook, importBook, LibraryError, listBooks } from '../../api/books'
import type { Book } from '../../api/books'
import ProcessingPanel from '../processing/ProcessingPanel'
import LearningGoals from '../goals/LearningGoals'
import BookProfilePanel from '../profiles/BookProfilePanel'

const asError = (error: unknown) => error instanceof LibraryError ? error : new LibraryError('Library request failed.')

export default function Library() {
  const [books, setBooks] = useState<Book[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [detail, setDetail] = useState<Book | null>(null)
  const [profileRefreshKey, setProfileRefreshKey] = useState(0)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [importError, setImportError] = useState<LibraryError | null>(null)
  const [deleteError, setDeleteError] = useState<LibraryError | null>(null)
  const [busy, setBusy] = useState<'import' | 'delete' | 'processing' | 'goal' | 'profile' | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [notice, setNotice] = useState('')
  const alive = useRef(false)
  const listRequest = useRef<AbortController | null>(null)
  const detailRequest = useRef<AbortController | null>(null)
  const mutation = useRef<AbortController | null>(null)
  const form = useRef<HTMLFormElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)
  const remove = useRef<HTMLButtonElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const detailsHeading = useRef<HTMLHeadingElement>(null)
  const opener = useRef<HTMLButtonElement | null>(null)

  async function refresh() {
    listRequest.current?.abort()
    const controller = new AbortController()
    listRequest.current = controller
    setLoading(true)
    setListError('')
    try {
      const result = await listBooks(controller.signal)
      if (alive.current && !controller.signal.aborted) setBooks(result)
    } catch (error) {
      if (alive.current && !controller.signal.aborted) setListError(asError(error).message)
    } finally {
      if (alive.current && !controller.signal.aborted) setLoading(false)
    }
  }

  useEffect(() => {
    alive.current = true
    void refresh()
    return () => {
      alive.current = false
      listRequest.current?.abort()
      detailRequest.current?.abort()
      mutation.current?.abort()
    }
  }, [])

  useEffect(() => { if (confirming) cancel.current?.focus() }, [confirming])
  useEffect(() => { if (detail && !detailLoading) detailsHeading.current?.focus() }, [detail, detailLoading])

  const updateBook = useCallback((book: Book) => {
    setDetail(current => current?.id === book.id ? book : current)
    setBooks(current => current.map(item => item.id === book.id ? book : item))
  }, [])

  async function openBook(id: string, button?: HTMLButtonElement) {
    detailRequest.current?.abort()
    const controller = new AbortController()
    detailRequest.current = controller
    if (button) opener.current = button
    setDetail(null)
    setDetailLoading(true)
    setDetailError('')
    setDeleteError(null)
    setConfirming(false)
    try {
      const book = await getBook(id, controller.signal)
      if (alive.current && !controller.signal.aborted) setDetail(book)
    } catch (error) {
      if (alive.current && !controller.signal.aborted) setDetailError(asError(error).message)
    } finally {
      if (alive.current && !controller.signal.aborted) setDetailLoading(false)
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (mutation.current) return
    const data = new FormData(event.currentTarget)
    const file = data.get('file')
    if (!(file instanceof File) || !file.size || file.size > 100 * 1024 * 1024) {
      setImportError(new LibraryError('Choose a non-empty PDF of at most 100 MiB.'))
      return
    }
    const controller = new AbortController()
    mutation.current = controller
    setBusy('import'); setImportError(null); setNotice('')
    try {
      const book = await importBook(data, controller.signal)
      if (!alive.current || controller.signal.aborted) return
      form.current?.reset()
      setNotice(`Imported ${book.title}.`)
      await refresh()
      if (alive.current) await openBook(book.id)
    } catch (error) {
      if (!alive.current || controller.signal.aborted) return
      const failure = asError(error)
      setImportError(failure)
      if (failure.code === 'outcome_unknown') await refresh()
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (alive.current && !controller.signal.aborted) setBusy(null)
    }
  }

  async function confirmDelete() {
    if (!detail || mutation.current) return
    const controller = new AbortController()
    mutation.current = controller
    setBusy('delete'); setDeleteError(null); setNotice('')
    try {
      await deleteBook(detail.id, controller.signal)
      if (!alive.current || controller.signal.aborted) return
      setDetail(null); setConfirming(false)
      setNotice(`Removed ${detail.title}.`)
      await refresh()
      heading.current?.focus()
    } catch (error) {
      if (!alive.current || controller.signal.aborted) return
      const failure = asError(error)
      setDeleteError(failure)
      if (['outcome_unknown', 'deletion_cleanup_pending'].includes(failure.code)) await refresh()
    } finally {
      if (mutation.current === controller) mutation.current = null
      if (alive.current && !controller.signal.aborted) setBusy(null)
    }
  }

  return <section aria-labelledby="library-heading">
    <h2 id="library-heading" ref={heading} tabIndex={-1}>Your PDF library</h2>
    <p>Keep your books on this computer. Import one PDF at a time, up to 100 MiB.</p>
    <form onSubmit={submit} ref={form}>
      <fieldset disabled={busy !== null}>
        <legend>Import a PDF</legend>
        <label htmlFor="pdf-file">PDF file</label>
        <input id="pdf-file" name="file" type="file" accept=".pdf,application/pdf" required />
        <details><summary>Optional book details</summary>
          <p>Leave blank to use the PDF title and author. Edition and publication year stay empty unless supplied.</p>
          <label>Title (optional)<input name="title" maxLength={500} /></label>
          <label>Author (optional)<input name="author" maxLength={500} /></label>
          <label>Edition (optional)<input name="edition" maxLength={100} /></label>
          <label>Publication year (optional)<input name="year" type="number" min={1} max={9999} step={1} /></label>
        </details>
        <button type="submit">{busy === 'import' ? 'Importing…' : 'Import PDF'}</button>
      </fieldset>
    </form>
    {importError && <div role="alert"><p>{importError.message}</p>
      {importError.existingBookId && <button disabled={busy !== null} onClick={() => void openBook(importError.existingBookId!)}>Open existing book</button>}
    </div>}
    <p role="status" aria-label="Library activity">{busy === 'import' ? 'Importing…' : busy === 'delete' ? 'Deleting…' : busy === 'processing' ? 'PDF processing is active.' : busy === 'goal' ? 'Learning goal update is active.' : busy === 'profile' ? 'Book profile update is active.' : notice}</p>
    <div className="library-toolbar"><h3>Books</h3><button disabled={loading || busy !== null} onClick={() => void refresh()}>Refresh library</button></div>
    {loading && <p role="status">Loading books…</p>}
    {listError && <div role="alert"><p>{listError}</p><button onClick={() => void refresh()}>Retry library</button></div>}
    {!loading && !listError && books.length === 0 && <p>No books yet. Import a PDF to begin.</p>}
    <ul className="book-list">{books.map(book => <li key={book.id}>
      <button disabled={busy !== null} onClick={event => void openBook(book.id, event.currentTarget)}>{book.title}</button>
      <span>{book.page_count} pages · {book.author || 'Author not provided'}</span>
      <span>Processing: {book.processing_status}</span>
      {!book.file_available && <span className="error">Local PDF is missing</span>}
    </li>)}</ul>
    {!loading && !listError && <LearningGoals books={books} disabled={busy !== null}
      profileRefreshKey={profileRefreshKey} onOpenBook={id => void openBook(id)}
      onBusyChange={active => setBusy(active ? 'goal' : null)} />}
    {detailLoading && <p role="status">Loading book details…</p>}
    {detailError && <p role="alert">{detailError} Select the book again to retry.</p>}
    {detail && <article aria-labelledby="book-heading">
      <h3 id="book-heading" tabIndex={-1} ref={detailsHeading}>{detail.title}</h3>
      <dl>{[
        ['Filename', detail.original_filename], ['Author', detail.author], ['Edition', detail.edition],
        ['Publication year', detail.year], ['Pages', detail.page_count],
        ['Size', `${(detail.size_bytes / 1024 / 1024).toFixed(2)} MiB`],
        ['Imported', new Date(detail.imported_at).toLocaleString()],
      ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? 'Not provided'}</dd></div>)}</dl>
      {!detail.file_available && <p role="alert">The local PDF is missing. You can remove this library entry.</p>}
      <ProcessingPanel book={detail} disabled={busy !== null}
        onBookChange={updateBook} onBusyChange={active => setBusy(active ? 'processing' : null)} />
      <BookProfilePanel book={detail} disabled={busy !== null}
        onSaved={() => setProfileRefreshKey(value => value + 1)}
        onBusyChange={active => setBusy(active ? 'profile' : null)} />
      {!confirming ? <button ref={remove} disabled={busy !== null || detail.processing_status === 'processing'} onClick={() => setConfirming(true)}>Remove book</button>
        : <div className="delete-confirm" role="group" aria-label="Confirm deletion">
          <p>Remove “{detail.title}”? Its local PDF and library entry will be permanently removed.</p>
          <p>Saved comparisons containing this book will also be permanently removed.</p>
          <button ref={cancel} disabled={busy !== null} onClick={() => { setConfirming(false); setDeleteError(null); setTimeout(() => remove.current?.focus(), 0) }}>Cancel</button>
          <button disabled={busy !== null} onClick={() => void confirmDelete()}>{deleteError ? 'Retry deletion' : 'Delete book'}</button>
        </div>}
      {deleteError && <p role="alert">{deleteError.message}</p>}
      <button disabled={busy !== null} onClick={() => { setDetail(null); setConfirming(false); opener.current?.focus() }}>Close details</button>
    </article>}
  </section>
}
