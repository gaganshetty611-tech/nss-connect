export function formatDate(value, opts = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!value) return '—'
  const d = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('en-IN', opts)
}

export function formatTime(value) {
  if (!value) return ''
  if (/^\d{2}:\d{2}/.test(value)) {
    const [h, m] = value.split(':').map(Number)
    const d = new Date()
    d.setHours(h, m, 0, 0)
    return d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
  }
  return new Date(value).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
}

export function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

export function timeAgo(value) {
  const diff = (Date.now() - new Date(value).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`
  return formatDate(value)
}

export function toISODate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export const pretty = (s) => (s ? String(s).replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()) : '')

/** Extract a check-in token from a scanned QR payload (full URL or bare token). */
export function extractToken(text) {
  if (!text) return null
  const trimmed = String(text).trim()
  const m = trimmed.match(/\/attendance\/check-in\/([A-Za-z0-9_-]{20,})/)
  if (m) return m[1]
  return /^[A-Za-z0-9_-]{20,}$/.test(trimmed) ? trimmed : null
}
