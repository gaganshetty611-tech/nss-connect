import { Suspense, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import notificationService from '../services/notificationService'
import { ROLES } from '../utils/constants'
import { trackPageView } from '../utils/analytics'
import CookieConsent, { OPEN_COOKIE_SETTINGS } from './CookieConsent'
import { Spinner } from './ui'
import useSeo from './useSeo'

function ApiStatus() {
  const [ok, setOk] = useState(null)
  useEffect(() => {
    let active = true
    const ping = () => api.get('/health/', { timeout: 5000 }).then(() => active && setOk(true)).catch(() => active && setOk(false))
    ping()
    const id = setInterval(ping, 30000)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [])
  const label = ok === null ? 'Connecting…' : ok ? 'Server online' : 'Server offline'
  const dot = ok === null ? 'bg-slate-400' : ok ? 'bg-green-600 animate-pulse' : 'bg-red-600'
  return (
    <span className="inline-flex items-center gap-1.5" role="status" aria-live="polite">
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
      {label}
    </span>
  )
}

function NavItem({ to, children, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `rounded-lg px-3 py-2 text-sm font-medium transition active:scale-95 ${isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:text-navy hover:bg-slate-100'}`
      }
    >
      {children}
    </NavLink>
  )
}

function NotificationBell() {
  const [count, setCount] = useState(0)
  const location = useLocation()
  useEffect(() => {
    let active = true
    const load = () => notificationService.unreadCount().then((n) => active && setCount(n)).catch(() => {})
    load()
    const id = setInterval(load, 60000)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [location.pathname])
  return (
    <Link to="/notifications" className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label={`Notifications (${count} unread)`}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </svg>
      {count > 0 && (
        <span className="absolute -right-0.5 -top-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
          {count > 99 ? '99+' : count}
        </span>
      )}
    </Link>
  )
}

function ProfileMenu() {
  const { user, logout, isAdmin } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const navigate = useNavigate()
  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])
  const initials = (user.full_name || user.email).split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
  return (
    <div className="relative" ref={ref}>
      <button className="flex items-center gap-2 rounded-xl p-1 pr-2 hover:bg-slate-100" onClick={() => setOpen((o) => !o)} aria-haspopup="menu">
        {user.photo_url ? (
          <img src={user.photo_url} alt="" className="h-8 w-8 rounded-full object-cover" />
        ) : (
          <span className="grid h-8 w-8 place-items-center rounded-full bg-navy text-xs font-bold text-white">{initials}</span>
        )}
        <span className="hidden text-left lg:block">
          <span className="block text-xs font-semibold leading-tight">{user.full_name}</span>
          <span className="block text-[11px] leading-tight text-slate-500">{ROLES[user.role]}</span>
        </span>
      </button>
      {open && (
        <div className="card absolute right-0 z-[1200] mt-2 w-56 p-2 text-sm" role="menu">
          {[
            ['/dashboard', 'Dashboard'],
            ['/profile', 'Profile'],
            ['/certificates', 'Certificates'],
            ['/calendar', 'Calendar'],
            ['/scan', 'Scan QR'],
            ['/nss-units', 'NSS Units'],
            ...(isAdmin ? [['/admin', 'Admin Panel']] : []),
          ].map(([to, label]) => (
            <Link key={to} to={to} className="block rounded-lg px-3 py-2 hover:bg-slate-100" onClick={() => setOpen(false)}>
              {label}
            </Link>
          ))}
          <button
            className="mt-1 block w-full rounded-lg px-3 py-2 text-left text-red-600 hover:bg-red-50"
            onClick={async () => {
              await logout()
              navigate('/login')
            }}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const { user, isAuthenticated } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname } = useLocation()
  useSeo()
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    trackPageView(pathname)
    window.scrollTo(0, 0)
  }, [pathname])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const close = () => setMenuOpen(false)
  const links = (
    <>
      <NavItem to="/events" onClick={close}>Explore Drives</NavItem>
      <NavItem to="/ngos" onClick={close}>NGO Hub</NavItem>
      <NavItem to="/analytics" onClick={close}>ABP Analytics</NavItem>
      {!isAuthenticated && <NavItem to="/register" onClick={close}>Register Account</NavItem>}
      <NavItem to="/events/new" onClick={close}>Host Drive</NavItem>
    </>
  )
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[1400] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-brand-700 focus:shadow-lg">Skip to main content</a>
      <header className={`sticky top-0 z-[1000] border-b border-ink/10 bg-paper/90 backdrop-blur transition-shadow duration-200 ${scrolled ? 'shadow-md' : ''}`}>
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
          <Link to={isAuthenticated ? '/dashboard' : '/events'} className="flex items-center gap-2.5 shrink-0">
            <img src="/nss-logo.png" alt="National Service Scheme logo" width="40" height="40" className="h-10 w-10 shrink-0 object-contain" />
            <span>
              <span className="flex items-center gap-1.5">
                <span className="font-display text-base font-bold tracking-tight text-navy">NSS Connect</span>
                <span className="rounded-sm bg-ochre-50 px-1.5 py-0.5 text-[10px] font-semibold text-ochre ring-1 ring-inset ring-ochre-100">AI-assisted</span>
              </span>
              <span className="hidden text-[11px] text-ink/50 sm:block">Volunteer–NGO Matching &amp; Verified ABP Tracking</span>
            </span>
          </Link>
          <nav className="ml-4 hidden items-center gap-1 lg:flex">{links}</nav>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            {isAuthenticated ? (
              <>
                {user.organization && (
                  <span className="hidden max-w-[220px] truncate rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 md:inline" title={user.organization.name}>
                    {user.organization.status === 'VERIFIED' && '✓ '}
                    {user.organization.name}
                  </span>
                )}
                <span className="hidden rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 sm:inline">{ROLES[user.role]}</span>
                <NotificationBell />
                <ProfileMenu />
              </>
            ) : (
              <Link to="/login" className="btn-secondary btn-sm">Log in</Link>
            )}
            <button className="btn-ghost btn-sm lg:hidden" onClick={() => setMenuOpen((o) => !o)} aria-label="Menu" aria-expanded={menuOpen}>
              ☰
            </button>
          </div>
        </div>
        {menuOpen && <nav className="flex flex-col gap-1 border-t border-slate-100 px-4 py-2 lg:hidden">{links}</nav>}
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 focus:outline-none sm:py-8">
        <div key={pathname} className="animate-page">
          <Suspense fallback={<Spinner />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-4 text-xs text-slate-500 sm:flex-row sm:justify-between">
          <span>© {new Date().getFullYear()} NSS Connect · NGOs, NSS units and volunteers on one platform · <ApiStatus /></span>
          <span>
            <Link to="/certificate/verify" className="hover:text-brand-700">Verify a certificate</Link> · <Link to="/calendar" className="hover:text-brand-700">Calendar</Link> ·{' '}
            <Link to="/privacy" className="hover:text-brand-700">Privacy Policy</Link> · <Link to="/terms" className="hover:text-brand-700">Terms &amp; Conditions</Link> ·{' '}
            <button type="button" className="hover:text-brand-700" onClick={() => window.dispatchEvent(new Event(OPEN_COOKIE_SETTINGS))}>Cookie settings</button>
          </span>
        </div>
      </footer>
      <CookieConsent />
    </div>
  )
}
