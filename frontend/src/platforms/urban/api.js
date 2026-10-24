import { req } from '../../api'

export const urbanApi = {
  cities: (asOf) => req(`/api/urban/cities?as_of=${asOf}`),
  cauvery: (asOf) => req(`/api/urban/cauvery?as_of=${asOf}`),
}
