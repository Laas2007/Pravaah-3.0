import { req } from '../../api'

export const urbanApi = {
  cities: (asOf) => req(`/api/urban/cities?as_of=${asOf}`),
  cauvery: (asOf) => req(`/api/urban/cauvery?as_of=${asOf}`),
  wards: (asOf) => req(`/api/urban/wards?as_of=${asOf}`),
  wardGeo: () => req('/api/wards.geojson'),
  demand: (asOf) => req(`/api/urban/demand?as_of=${asOf}`),
  leaksDemo: () => req('/api/urban/leaks/demo'),
  leaksCheck: (csv) => req('/api/urban/leaks/check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ csv }) }),
}
