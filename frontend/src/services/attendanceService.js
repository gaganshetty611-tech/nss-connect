import api from './api'

const attendanceService = {
  generateQR: (eventId) => api.post(`/events/${eventId}/qr/`).then((r) => r.data),
  currentQR: (eventId) => api.get(`/events/${eventId}/qr/`).then((r) => r.data),
  scanStatus: (token) => api.get('/attendance/scan-status/', { params: { token } }).then((r) => r.data),
  checkIn: (token) => api.post('/attendance/check-in/', { token }).then((r) => r.data),
  checkOut: (token) => api.post('/attendance/check-out/', { token }).then((r) => r.data),
  forEvent: (eventId) => api.get(`/events/${eventId}/attendance/`).then((r) => r.data),
  markAbsent: (eventId) => api.post(`/events/${eventId}/attendance/mark-absent/`).then((r) => r.data),
  list: (params) => api.get('/attendance/', { params }).then((r) => r.data),
  feedback: (eventId) => api.get(`/events/${eventId}/feedback/`).then((r) => r.data),
  submitFeedback: (eventId, rating, comments) => api.post(`/events/${eventId}/feedback/`, { rating, comments }).then((r) => r.data),
}
export default attendanceService
