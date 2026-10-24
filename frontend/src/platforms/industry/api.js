import { req } from '../../api'

export const industryApi = {
  areas: (asOf) => req(`/api/industry/areas?as_of=${asOf}`),
  location: (lat, lon, asOf) => req(`/api/industry/location?lat=${lat}&lon=${lon}&as_of=${asOf}`),
}
