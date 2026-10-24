import { req } from '../../api'

export const industryApi = {
  areas: (asOf) => req(`/api/industry/areas?as_of=${asOf}`),
  districts: (asOf) => req(`/api/industry/districts?as_of=${asOf}`),
  location: (lat, lon, asOf) => req(`/api/industry/location?lat=${lat}&lon=${lon}&as_of=${asOf}`),
  feasibility: ({ lat, lon, kld, gw, ha, asOf }) => req(`/api/industry/feasibility?lat=${lat}&lon=${lon}&demand_kld=${kld}&as_of=${asOf}`
    + (gw != null ? `&gw_share=${gw}` : '') + (ha ? `&site_area_ha=${ha}` : '')),
}
