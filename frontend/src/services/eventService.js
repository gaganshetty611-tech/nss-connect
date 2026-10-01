import api, { toFormData } from './api'

function payload(data) {
  // Use multipart only when an image file is attached.
  return data.event_image instanceof File ? toFormData(data) : (({ event_image, ...rest }) => rest)(data)
}

const eventService = {
  list: (params) => api.get('/events/', { params }).then((r) => r.data),
  get: (id) => api.get(`/events/${id}/`).then((r) => r.data),
  create: (data) => api.post('/events/', payload(data)).then((r) => r.data),
  update: (id, data) => api.patch(`/events/${id}/`, payload(data)).then((r) => r.data),
  remove: (id) => api.delete(`/events/${id}/`),
  approve: (id, note) => api.post(`/events/${id}/approve/`, { note }).then((r) => r.data),
  reject: (id, note) => api.post(`/events/${id}/reject/`, { note }).then((r) => r.data),
  setStatus: (id, status) => api.post(`/events/${id}/set-status/`, { status }).then((r) => r.data),
  calendar: (params) => api.get('/events/calendar/', { params }).then((r) => r.data),
  map: (params) => api.get('/events/map/', { params }).then((r) => r.data),
  skills: () => api.get('/events/skills/').then((r) => r.data),
  photos: (id) => api.get(`/events/${id}/photos/`).then((r) => r.data),
  uploadPhoto: (id, photo, caption, coords) =>
    api.post(`/events/${id}/photos/`, toFormData({ photo, caption, latitude: coords?.latitude, longitude: coords?.longitude })).then((r) => r.data),
  deletePhoto: (photoId) => api.delete(`/photos/${photoId}/`),
  groupApply: (id, data) => api.post(`/events/${id}/group-apply/`, data).then((r) => r.data),
  groupApplications: (id) => api.get(`/events/${id}/group-applications/`).then((r) => r.data),
  decideGroup: (gaId, decision) => api.post(`/group-applications/${gaId}/${decision}/`).then((r) => r.data),
  inviteUnit: (id, nss_unit, message, notify_members) => api.post(`/events/${id}/invite-unit/`, { nss_unit, message, notify_members }).then((r) => r.data),
  // AI
  recommendations: (id) => api.get(`/events/${id}/recommendations/`).then((r) => r.data),
  turnout: (id) => api.get(`/events/${id}/turnout-estimate/`).then((r) => r.data),
  summary: (id, organizer_notes) => api.post(`/events/${id}/summary/`, { organizer_notes }).then((r) => r.data),
  categorize: (title, description) => api.post('/ai/categorize/', { title, description }).then((r) => r.data),
  suggestDatetime: (category) => api.get('/ai/suggest-datetime/', { params: { category } }).then((r) => r.data),
  // Emergency
  emergencyList: (params) => api.get('/emergency-requests/', { params }).then((r) => r.data),
  emergencyCreate: (data) => api.post('/emergency-requests/', data).then((r) => r.data),
}
export default eventService
