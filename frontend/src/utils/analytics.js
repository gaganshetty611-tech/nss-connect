// Google Analytics 4 – loaded ONLY after the visitor accepts cookies.
// VITE_GA_ID is a public measurement ID (G-XXXXXXXXXX), not a secret. Empty = analytics disabled.
const KEY = 'nss_cookie_consent'
const GA_ID = (import.meta.env.VITE_GA_ID || '').trim()
let loaded = false

export function getConsent() {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setConsent(value) {
  try {
    localStorage.setItem(KEY, value)
  } catch {
    /* storage blocked – choice applies to this visit only */
  }
  if (value === 'accepted') loadAnalytics()
}

export function loadAnalytics() {
  if (loaded || !/^G-[A-Z0-9]+$/i.test(GA_ID)) return
  loaded = true
  window.dataLayer = window.dataLayer || []
  window.gtag = function gtag() {
    window.dataLayer.push(arguments)
  }
  window.gtag('js', new Date())
  window.gtag('config', GA_ID, { send_page_view: false, anonymize_ip: true })
  const s = document.createElement('script')
  s.async = true
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_ID)}`
  document.head.appendChild(s)
}

export function trackPageView(path = window.location.pathname + window.location.search) {
  if (getConsent() !== 'accepted' || !window.gtag) return
  window.gtag('event', 'page_view', { page_path: path, page_title: document.title })
}

export function trackEvent(name, params = {}) {
  if (getConsent() !== 'accepted' || !window.gtag) return
  window.gtag('event', name, params)
}
