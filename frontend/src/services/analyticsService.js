import api, { downloadFile } from './api'

const analyticsService = {
  analytics: (params) => api.get('/analytics/', { params }).then((r) => r.data),
  volunteerDashboard: () => api.get('/dashboard/volunteer/').then((r) => r.data),
  organizerDashboard: () => api.get('/dashboard/organizer/').then((r) => r.data),
  adminDashboard: () => api.get('/dashboard/admin/').then((r) => r.data),
  reportTypes: () => api.get('/reports/types/').then((r) => r.data),
  reportPreview: (type, params) => api.get('/reports/', { params: { ...params, type, export: 'json' } }).then((r) => r.data),
  exportReport: (type, exportFormat, params) =>
    downloadFile('/reports/', { ...params, type, export: exportFormat }, `nss-connect-${type}.${exportFormat}`),
}
export default analyticsService
