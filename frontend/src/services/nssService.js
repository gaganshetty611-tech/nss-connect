import api from './api'

const nssService = {
  universities: () => api.get('/universities/').then((r) => r.data),
  colleges: (params) => api.get('/colleges/', { params }).then((r) => r.data),
  list: (params) => api.get('/nss-units/', { params }).then((r) => r.data),
  get: (id) => api.get(`/nss-units/${id}/`).then((r) => r.data),
  stats: (id) => api.get(`/nss-units/${id}/stats/`).then((r) => r.data),
  members: (id) => api.get(`/nss-units/${id}/members/`).then((r) => r.data),
  create: (data) => api.post('/nss-units/', data).then((r) => r.data),
  update: (id, data) => api.patch(`/nss-units/${id}/`, data).then((r) => r.data),
  verify: (id, note) => api.post(`/nss-units/${id}/verify/`, { note }).then((r) => r.data),
  reject: (id, note) => api.post(`/nss-units/${id}/reject/`, { note }).then((r) => r.data),
  suspend: (id, note) => api.post(`/nss-units/${id}/suspend/`, { note }).then((r) => r.data),
}
export default nssService
