import { roleLabels } from '../../api/bookComparisons'
import type { Judgment, Preview } from '../../api/bookComparisons'

const readable = (value: string | null | undefined) => value ? value.replaceAll('_', ' ') : 'Unknown'

export default function ComparisonFacts({ preview, judgments = [] }: {
  preview: Preview; judgments?: Judgment[]
}) {
  const name = (id: string) => preview.books.find(b => b.book_id === id)?.title || id
  return <div>
    <p>Goal: <strong>{preview.goal.title}</strong>{preview.goal.description && ` — ${preview.goal.description}`}</p>
    <p>Overlap describes listed profile topics only. Exact matches ignore case and repeated whitespace;
      synonyms, acronyms and meaning are not matched. Display order is not study order.</p>
    <div className="comparison-scroll"><table>
      <caption>Book comparison overview</caption>
      <thead><tr>{['Book', 'Difficulty (profile)', 'Orientation (profile)', 'Depth (manual)',
        'Practice (manual)', 'Relevance (manual)', 'Role (manual)'].map(v => <th scope="col" key={v}>{v}</th>)}</tr></thead>
      <tbody>{preview.books.map(book => {
        const j = judgments.find(j => j.book_id === book.book_id)
        return <tr key={book.book_id}><th scope="row">{book.title}</th>
          <td data-label="Difficulty (profile)">{readable(book.profile.difficulty)}</td><td data-label="Orientation (profile)">{readable(book.profile.orientation)}</td>
          <td data-label="Depth (manual)">{readable(j?.depth?.category)}</td><td data-label="Practice (manual)">{readable(j?.practice?.category)}</td>
          <td data-label="Relevance (manual)">{readable(j?.relevance.category)}</td><td data-label="Role (manual)">{j ? roleLabels[j.role] : 'Not assigned'}</td></tr>
      })}</tbody>
    </table></div>
    {preview.books.map(book => {
      const j = judgments.find(j => j.book_id === book.book_id)
      return <details key={book.book_id}><summary>{book.title} — profile facts and rationale</summary>
        <p>{book.topic_count} listed topics. Listed only in this book: {book.unique_topics.join('; ') || 'None'}.</p>
        <dl>{Object.entries(book.profile.provenance).map(([field, source]) => {
          const value = book.profile[field as keyof typeof book.profile]
          const display = Array.isArray(value) ? value.join('; ') : typeof value === 'string' ? value : ''
          return <div key={field}><dt>{field.replaceAll('_', ' ')}</dt>
            <dd>{display || (field === 'prerequisites' ? 'Prerequisites not recorded' : 'Not recorded')}
              {source && <small> — Profile input: {readable(source)}</small>}</dd></div>
        })}</dl>
        {j && <div><p>Role: {roleLabels[j.role]} — Manual judgment</p><p>{j.rationale}</p>
          <p>Relevance: {j.relevance.category} — {j.relevance.explanation}</p>
          <p>Depth: {j.depth ? `${readable(j.depth.category)} — ${j.depth.explanation}` : 'Unknown'}</p>
          <p>Practice content: {j.practice ? `${j.practice.category} — ${j.practice.explanation}` : 'Unknown'}</p>
          <p>Focus topics: {j.focus_topics.join('; ') || 'None recorded'}</p>
          <p>Evidence references: {j.evidence_refs.map(ref => ref.kind === 'profile_field' ? `Profile ${ref.field}`
            : ref.kind === 'topic' ? `Topic ${ref.topic}` : `${ref.dimension} with ${name(ref.other_book_id)}`).join('; ') || 'Learner explanation only'}</p>
          <p>These judgments are entered by the learner, not verified against PDF content.</p>
        </div>}
      </details>
    })}
    <details><summary>Topic coverage — derived</summary><ul>{preview.coverage.map(row =>
      <li key={row.topic}>{row.topic}: {row.book_ids.map(name).join('; ')}</li>)}</ul></details>
    <details><summary>Pairwise overlap, difficulty and prerequisites — derived</summary>
      {preview.pairs.map(pair => <section key={pair.left_book_id + pair.right_book_id}>
        <h5>{name(pair.left_book_id)} / {name(pair.right_book_id)}</h5>
        <p>Difficulty of first relative to second: {pair.difficulty}.</p>
        <p>Shared listed topics: {pair.overlap.shared.join('; ') || 'None'}</p>
        <p>Only first: {pair.overlap.left_only.join('; ') || 'None'}</p>
        <p>Only second: {pair.overlap.right_only.join('; ') || 'None'}</p>
        {pair.prerequisites ? <><p>Shared listed prerequisites: {pair.prerequisites.shared.join('; ') || 'None'}</p>
          <p>Prerequisites only first: {pair.prerequisites.left_only.join('; ') || 'None'}</p>
          <p>Prerequisites only second: {pair.prerequisites.right_only.join('; ') || 'None'}</p></>
          : <p>Prerequisite comparison unknown: prerequisites not recorded for one or both books.</p>}
        <small>Sources: the two captured profiles’ main topics, difficulty and prerequisites.
          Matching rule: {preview.algorithm_version}.</small>
      </section>)}
    </details>
  </div>
}
