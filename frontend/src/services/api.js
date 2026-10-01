import axios from 'axios'

/**
 * Axios instance for the Django REST API.
 *
 * Token handling:
 *  - The short-lived ACCESS token lives only in memory (this module).
 *  - The REFRESH token is an httpOnly cookie set by Django (never readable by JS, never in localStorage).
 *  - On a 401 we call /auth/token/refresh/ once (concurrent requests wait for the same refresh) and retry.
 */
export const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: 30000,
})

let accessToken = null
let refreshPromise = null
let onSessionExpired = () => {}

export function setAccessToken(token) {
  accessToken = token
}
export function getAccessToken() {
  return accessToken
}
export function setSessionExpiredHandler(fn) {
  onSessionExpired = fn
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

export function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_URL}/auth/token/refresh/`, {}, { withCredentials: true })
      .then((res) => {
        setAccessToken(res.data.access)
        return res.data
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

const NO_RETRY = ['/auth/login/', '/auth/token/refresh/', '/auth/register/', '/auth/logout/']

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    if (status === 401 && original && !original._retried && !NO_RETRY.some((p) => original.url?.includes(p))) {
      original._retried = true
      try {
        await refreshAccessToken()
        original.headers.Authorization = `Bearer ${accessToken}`
        return api(original)
      } catch (refreshError) {
        setAccessToken(null)
        onSessionExpired()
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  },
)

/** Turn a DRF error response into one readable string. */
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error?.response) return error?.message === 'Network Error' ? 'Cannot reach the server. Is the backend running?' : fallback
  const status = error.response.status
  // Vite's dev proxy answers 500/502/503/504 with an empty body when Django isn't running.
  if ([502, 503, 504].includes(status) || (status === 500 && !error.response.data)) {
    return 'Cannot reach the server. Is the backend running? (start it with scripts\\start.bat or scripts/start.sh)'
  }
  const data = error.response.data
  if (!data) return fallback
  if (typeof data === 'string') return data.startsWith('<') ? fallback : data
  if (data.detail) return String(data.detail)
  const parts = []
  for (const [field, msgs] of Object.entries(data)) {
    const text = Array.isArray(msgs) ? msgs.join(' ') : typeof msgs === 'object' ? JSON.stringify(msgs) : String(msgs)
    parts.push(field === 'non_field_errors' ? text : `${field.replace(/_/g, ' ')}: ${text}`)
  }
  return parts.join(' • ') || fallback
}

/** Field-level errors for react-hook-form: { field: 'message' } */
export function fieldErrors(error) {
  const data = error?.response?.data
  if (!data || typeof data !== 'object') return {}
  const out = {}
  for (const [k, v] of Object.entries(data)) out[k] = Array.isArray(v) ? v.join(' ') : String(v)
  return out
}

/** Download a binary endpoint (PDF/CSV) with auth and save it. */
export async function downloadFile(url, params = {}, fallbackName = 'download') {
  const path = url.startsWith(API_URL) ? url.slice(API_URL.length) : url.replace(/^\/api/, '')
  const res = await api.get(path, { params, responseType: 'blob' })
  const disposition = res.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const name = match ? match[1] : fallbackName
  const href = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = href
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

/** Build multipart FormData from a plain object (arrays become repeated keys). */
export function toFormData(obj) {
  const fd = new FormData()
  Object.entries(obj).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return
    if (Array.isArray(v)) v.forEach((item) => fd.append(k, item))
    else fd.append(k, v)
  })
  return fd
}

export default api
