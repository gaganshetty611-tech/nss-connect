import api, { downloadFile } from './api'

const certificateService = {
  list: (params) => api.get('/certificates/', { params }).then((r) => r.data),
  download: (cert) => downloadFile(cert.download_url, {}, `${cert.certificate_id}.pdf`),
  verify: (certificateId) => api.get(`/certificates/${encodeURIComponent(certificateId)}/verify/`).then((r) => r.data),
  revoke: (id, revoked = true) => api.post(`/certificates/${id}/revoke/`, { revoked }).then((r) => r.data),
}
export default certificateService
