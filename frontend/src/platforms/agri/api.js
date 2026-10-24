import { req } from '../../api'

export const agriApi = {
  taluk: (idx, asOf) => req(`/api/agri/taluk/${idx}?as_of=${asOf}`),
  crops: (idx, asOf) => req(`/api/agri/crops/${idx}?as_of=${asOf}`),
  drought: (asOf, idx) => req(`/api/core/drought?as_of=${asOf}${idx != null ? `&idx=${idx}` : ''}`),
  irrigation: (idx, crop, asOf) => req(`/api/agri/irrigation/${idx}?crop=${encodeURIComponent(crop)}&as_of=${asOf}`),
  sowing: (idx, crop, asOf) => req(`/api/agri/sowing/${idx}?crop=${encodeURIComponent(crop)}&as_of=${asOf}`),
}
