import api from './api'

const applicationService = {
  register: (eventId, data = {}) => api.post(`/events/${eventId}/register/`, data).then((r) => r.data),
  cancel: (eventId) => api.post(`/events/${eventId}/cancel/`).then((r) => r.data),
  forEvent: (eventId, params) => api.get(`/events/${eventId}/applications/`, { params }).then((r) => r.data),
  list: (params) => api.get('/applications/', { params }).then((r) => r.data),
  approve: (id) => api.post(`/applications/${id}/approve/`).then((r) => r.data),
  reject: (id) => api.post(`/applications/${id}/reject/`).then((r) => r.data),
  waitlist: (id) => api.post(`/applications/${id}/waitlist/`).then((r) => r.data),
}
export default applicationService
