import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const BRAND = 'NSS Connect'
const HOME_TITLE = 'NSS Connect – Volunteer–NGO Matching & Verified ABP Tracking'
const HOME_DESC = 'NSS Connect links NSS units and student volunteers with verified NGOs. Find drives, check in with QR codes, track ABP hours and earn verified certificates.'

// [pattern, title, description, noindex]
const PAGES = [
  [/^\/$/, HOME_TITLE, HOME_DESC],
  [/^\/events$/, 'Explore Volunteering Drives', 'Browse approved volunteering drives from verified NGOs and NSS units. Filter by category, date, location and skills.'],
  [/^\/events\/new$/, 'Host a Drive', 'Create a volunteering drive for your NGO or NSS unit and reach student volunteers.', true],
  [/^\/events\/[^/]+$/, 'Drive Details', 'Details, schedule, location and registration for this volunteering drive.'],
  [/^\/events\/[^/]+\/(edit|applications|attendance)$/, 'Manage Drive', 'Manage your volunteering drive.', true],
  [/^\/calendar$/, 'Drive Calendar', 'See upcoming NSS and NGO volunteering drives on a calendar.'],
  [/^\/ngos$/, 'NGO Hub', 'Discover verified NGOs running volunteering drives near you.'],
  [/^\/ngos\/new$/, 'Register an NGO', 'Register your NGO to post volunteering drives.', true],
  [/^\/ngos\/[^/]+$/, 'NGO Profile', 'NGO profile, verification status and upcoming drives.'],
  [/^\/ngos\/[^/]+\/edit$/, 'Edit NGO', 'Edit NGO details.', true],
  [/^\/nss-units$/, 'NSS Units', 'Find NSS units by college and university.'],
  [/^\/nss-units\/[^/]+$/, 'NSS Unit Profile', 'NSS unit profile, volunteers and activity.'],
  [/^\/analytics$/, 'ABP Analytics', 'Aggregate participation and ABP hours across NSS units and NGOs.'],
  [/^\/certificate\/verify$/, 'Verify a Certificate', 'Check that an NSS Connect volunteering certificate is genuine.'],
  [/^\/certificate\/[^/]+\/verify$/, 'Certificate Verification', 'Certificate verification result.'],
  [/^\/login$/, 'Log In', 'Log in to your NSS Connect account.'],
  [/^\/register$/, 'Create Your Free Account', 'Join NSS Connect as a volunteer, NSS coordinator or NGO organizer. It is free.'],
  [/^\/(forgot-password|reset-password|verify-email|auth\/google\/callback)$/, 'Account', 'Manage your NSS Connect account.', true],
  [/^\/privacy$/, 'Privacy Policy', 'How NSS Connect collects, uses and protects your personal data.'],
  [/^\/terms$/, 'Terms & Conditions', 'The terms that apply when you use NSS Connect.'],
  [/^\/(dashboard|profile|notifications|certificates|scan|attendance\/.*|admin.*)$/, 'Your Account', 'Your NSS Connect account.', true],
]

function setMeta(selector, create, value) {
  let el = document.head.querySelector(selector)
  if (!el) {
    el = create()
    document.head.appendChild(el)
  }
  el.setAttribute(el.tagName === 'LINK' ? 'href' : 'content', value)
}

const meta = (attr, key) => () => {
  const el = document.createElement('meta')
  el.setAttribute(attr, key)
  return el
}

/** Sets a unique <title>, meta description, Open Graph tags, canonical URL and robots for the current route. */
export default function useSeo() {
  const { pathname } = useLocation()
  useEffect(() => {
    const path = pathname.length > 1 ? pathname.replace(/\/$/, '') : pathname
    const hit = PAGES.find(([re]) => re.test(path))
    const [, title, description, noindex] = hit || [null, 'Page Not Found', 'This page does not exist on NSS Connect.', true]
    const full = title === HOME_TITLE ? title : `${title} | ${BRAND}`
    const url = `${window.location.origin}${path}`
    document.title = full
    setMeta('meta[name="description"]', meta('name', 'description'), description)
    setMeta('meta[property="og:title"]', meta('property', 'og:title'), full)
    setMeta('meta[property="og:description"]', meta('property', 'og:description'), description)
    setMeta('meta[property="og:url"]', meta('property', 'og:url'), url)
    setMeta('meta[name="twitter:title"]', meta('name', 'twitter:title'), full)
    setMeta('meta[name="twitter:description"]', meta('name', 'twitter:description'), description)
    setMeta('meta[name="robots"]', meta('name', 'robots'), noindex ? 'noindex, nofollow' : 'index, follow')
    setMeta('link[rel="canonical"]', () => Object.assign(document.createElement('link'), { rel: 'canonical' }), url)
  }, [pathname])
}
