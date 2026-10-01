import api, { downloadFile, toFormData } from './api'

function payload(data) {
  return data.logo instanceof File ? toFormData({ ...data, focus_areas: (data.focus_areas || []).join(',') }) : (({ logo, ...rest }) => rest)(data)
}

const ngoService = {
  list: (params) => api.get('/ngos/', { params }).then((r) => r.data),
  get: (id) => api.get(`/ngos/${id}/`).then((r) => r.data),
  create: (data) => api.post('/ngos/', payload(data)).then((r) => r.data),
  update: (id, data) => api.patch(`/ngos/${id}/`, payload(data)).then((r) => r.data),
  verify: (id, note) => api.post(`/ngos/${id}/verify/`, { note }).then((r) => r.data),
  reject: (id, note) => api.post(`/ngos/${id}/reject/`, { note }).then((r) => r.data),
  suspend: (id, note) => api.post(`/ngos/${id}/suspend/`, { note }).then((r) => r.data),
  documents: (id) => api.get(`/ngos/${id}/documents/`).then((r) => r.data),
  uploadDocument: (id, document_type, file) => api.post(`/ngos/${id}/documents/`, toFormData({ document_type, file })).then((r) => r.data),
  reviewDocument: (docId, status, note) => api.post(`/documents/${docId}/review/`, { status, note }).then((r) => r.data),
  downloadDocument: (doc) => downloadFile(doc.download_url, {}, doc.original_filename || 'document'),
}
export default ngoService
