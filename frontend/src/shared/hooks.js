import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { core } from '../api'

// Fetch-once caches for data every platform needs.
let metaP, taluksP
export const getMeta = () => (metaP ??= core.meta())
export const getTaluks = () => (taluksP ??= core.taluks())

/** {idx, name} of a taluk (from the cached boundary file), or null. */
export function useTaluk(idx) {
  const geo = useLoad(getTaluks, []).data
  if (idx == null || !geo) return null
  const f = geo.features.find((x) => x.properties.idx === idx)
  return f ? { idx, name: f.properties.name, district: f.properties.district } : null
}

/** Run an async loader whenever deps change; ignores stale responses. */
export function useLoad(loader, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  useEffect(() => {
    let live = true
    setState((s) => ({ ...s, loading: true }))
    loader()
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((error) => live && setState({ data: null, error: error.message, loading: false }))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

/** A selected index kept in the URL (?taluk=132 / ?w=17) so demo links can open it directly. */
function useIndexParam(name) {
  const [params, setParams] = useSearchParams()
  const raw = params.get(name)
  const sel = raw == null || raw === '' || Number.isNaN(Number(raw)) ? null : Number(raw)
  const setSel = (i) => setParams((p) => { if (i == null) p.delete(name); else p.set(name, String(i)); return p }, { replace: true })
  return [sel, setSel]
}
export const useTalukSel = () => useIndexParam('taluk')

/** Taluk (?taluk=) or Bengaluru ward (?w=, idx 0..242) selection; choosing one clears the other in one URL update. */
export function usePlaceSel() {
  const [params, setParams] = useSearchParams()
  const num = (k) => { const v = params.get(k); return v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v) }
  const pick = (key, i) => setParams((p) => {
    p.delete('taluk'); p.delete('w')
    if (i != null) p.set(key, String(i))
    return p
  }, { replace: true })
  return { taluk: num('taluk'), ward: num('w'), selectTaluk: (i) => pick('taluk', i), selectWard: (i) => pick('w', i) }
}

/** The shared "as of" date lives in the URL (?as_of=YYYY-MM-DD) so it survives switching platforms. */
export function useAsOf() {
  const [params, setParams] = useSearchParams()
  const meta = useLoad(getMeta, []).data
  const asOf = params.get('as_of') || meta?.climate_until || null
  const setAsOf = (d) => setParams((p) => { p.set('as_of', d); return p }, { replace: true })
  return [asOf, setAsOf, meta]
}
