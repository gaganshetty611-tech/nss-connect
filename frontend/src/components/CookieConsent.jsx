import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getConsent, setConsent, trackPageView } from '../utils/analytics'

export const OPEN_COOKIE_SETTINGS = 'nss:cookie-settings'

export default function CookieConsent() {
  const [open, setOpen] = useState(() => getConsent() === null)

  useEffect(() => {
    const show = () => setOpen(true)
    window.addEventListener(OPEN_COOKIE_SETTINGS, show)
    return () => window.removeEventListener(OPEN_COOKIE_SETTINGS, show)
  }, [])

  if (!open) return null

  const choose = (value) => {
    setConsent(value)
    setOpen(false)
    if (value === 'accepted') trackPageView()
  }

  return (
    <div role="dialog" aria-label="Cookie preferences" className="fixed inset-x-0 bottom-0 z-[1300] p-3 sm:p-4">
      <div className="card mx-auto flex max-w-3xl flex-col gap-3 p-4 shadow-xl sm:flex-row sm:items-center">
        <p className="text-sm text-slate-700">
          We use essential cookies to keep you signed in. With your permission we also use analytics cookies to understand how the site is used.
          See our <Link to="/privacy" className="font-semibold text-brand-700 underline">Privacy Policy</Link>.
        </p>
        <div className="flex shrink-0 gap-2">
          <button type="button" className="btn-secondary btn-sm" onClick={() => choose('rejected')}>Essential only</button>
          <button type="button" className="btn-primary btn-sm" onClick={() => choose('accepted')}>Accept analytics</button>
        </div>
      </div>
    </div>
  )
}
