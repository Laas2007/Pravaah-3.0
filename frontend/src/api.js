export async function req(path, opts) {
  const r = await fetch(path, opts)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

export const api = {
  meta: () => req('/api/meta'),
  geojson: () => req('/api/wards.geojson'),
  predict: (asOf) => req(`/api/predict?as_of=${asOf}`),
  ward: (idx, asOf) => req(`/api/ward/${idx}?as_of=${asOf}`),
  explanations: (asOf) => req(`/api/explanations?as_of=${asOf}`),
  backtest: () => req('/api/backtest'),
  intervene: (body) => req('/api/intervene', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  chat: (body) => req('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
}

// Karnataka core endpoints shared by all platforms (each platform keeps its own calls in platforms/<name>/api.js)
export const core = {
  meta: () => req('/api/core/meta'),
  taluks: () => req('/api/core/taluks.geojson'),
  districts: () => req('/api/core/districts.geojson'),
  indicators: (asOf) => req(`/api/core/indicators?as_of=${asOf}`),
  taluk: (idx, asOf) => req(`/api/core/taluk/${idx}?as_of=${asOf}`),
}
