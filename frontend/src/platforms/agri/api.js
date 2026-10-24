import { req } from '../../api'

export const agriApi = {
  taluk: (idx, asOf) => req(`/api/agri/taluk/${idx}?as_of=${asOf}`),
}
