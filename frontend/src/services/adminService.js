import api from './api'

const adminService = {
  users: (params) => api.get('/admin/users/', { params }).then((r) => r.data),
  updateUser: (id, data) => api.patch(`/admin/users/${id}/`, data).then((r) => r.data),
  suspend: (id) => api.post(`/admin/users/${id}/suspend/`).then((r) => r.data),
  activate: (id) => api.post(`/admin/users/${id}/activate/`).then((r) => r.data),
}
export default adminService
