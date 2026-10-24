import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { core } from '../api'

// Fetch-once caches for data every platform needs.
let metaP, taluksP
export const getMeta = () => (metaP ??= core.meta())
export const getTaluks = () => (taluksP ??= core.taluks())

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

/** The shared "as of" date lives in the URL (?as_of=YYYY-MM-DD) so it survives switching platforms. */
export function useAsOf() {
  const [params, setParams] = useSearchParams()
  const meta = useLoad(getMeta, []).data
  const asOf = params.get('as_of') || meta?.climate_until || null
  const setAsOf = (d) => setParams((p) => { p.set('as_of', d); return p }, { replace: true })
  return [asOf, setAsOf, meta]
}
