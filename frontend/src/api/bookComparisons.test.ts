import { afterEach, expect, it, vi } from 'vitest'
import { getComparison, putComparison, evidenceOptions } from './bookComparisons'
import { comparisonRequest, readyComparison, savedComparison } from '../test/comparisonFixtures'

afterEach(() => vi.unstubAllGlobals())
it('reads validated comparison and sends only explicit manual input', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(savedComparison()), { status: 200 }))
  vi.stubGlobal('fetch', fetch)
  expect((await getComparison('goal')).saved?.revision).toBe(1)
  fetch.mockResolvedValue(new Response(JSON.stringify(savedComparison()), { status: 200 }))
  await putComparison('goal', comparisonRequest())
  expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual(comparisonRequest())
})
it('rejects malformed responses and treats a malformed save as unknown', async () => {
  const malformed = savedComparison()
  malformed.saved!.books[0].provenance.role = 'derived' as 'manual'
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(malformed), { status: 200 })))
  vi.stubGlobal('fetch', fetch)
  await expect(getComparison('goal')).rejects.toThrow('Unexpected comparison response')
  await expect(putComparison('goal', comparisonRequest())).rejects.toMatchObject({ code: 'outcome_unknown' })
})
it('preserves structured revision-conflict errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: {
    code: 'comparison_revision_conflict', message: 'Reload and review.' } }), { status: 409 })))
  await expect(putComparison('goal', comparisonRequest())).rejects.toMatchObject({ code: 'comparison_revision_conflict' })
})
it('offers only populated own fields and known pair evidence', () => {
  const preview = readyComparison().current!
  const options = evidenceOptions(preview.books[0], preview)
  expect(options.some(o => o.value.kind === 'profile_field' && o.value.field === 'prerequisites')).toBe(false)
  expect(options.some(o => o.value.kind === 'pair' && o.value.dimension === 'prerequisites')).toBe(false)
  expect(options.some(o => o.value.kind === 'topic' && o.value.topic === 'algorithms')).toBe(true)
})
