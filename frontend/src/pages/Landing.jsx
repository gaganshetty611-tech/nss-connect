import { Link } from 'react-router-dom'
import EventCard from '../components/EventCard'
import { RosterRowSkeleton, ErrorAlert } from '../components/ui'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { CONTACT_EMAIL } from '../utils/site'

const STEPS = [
  ['1', 'Find a drive', 'Browse approved drives from verified NGOs, filtered by cause, date, location and your skills.'],
  ['2', 'Check in with a QR code', 'Scan at the venue to check in and out. No paper registers, no lost attendance sheets.'],
  ['3', 'Get a verified certificate', 'Certificates are generated automatically after verified participation, with ABP 1 / ABP 2 hours tracked separately.'],
]

const FAQS = [
  ['Is NSS Connect free?', 'Yes. Creating an account, joining drives and downloading your certificates are free for volunteers, NSS coordinators and NGOs.'],
  ['Who can host a drive?', 'Only verified NGOs and NSS units. NGO organizers upload verification documents, and an administrator approves the NGO before any drive goes live.'],
  ['How is my attendance verified?', 'Organizers show a QR code at the venue. You scan it to check in and out, and the platform applies time rules so hours can be trusted.'],
  ['Can I check that a certificate is genuine?', 'Yes. Every certificate has an ID that anyone can enter on the Verify a certificate page.'],
  ['How do I get help?', `Email ${CONTACT_EMAIL}. We aim to reply within 1 business day.`],
]

function OpenDrives() {
  const { data, loading, error, reload } = useAsync(() => eventService.list({ page_size: 4, available: 'true' }), [])
  const drives = data?.results || []
  return (
    <section aria-labelledby="open-drives" className="mx-auto max-w-3xl py-10">
      <div className="flex items-end justify-between gap-3 border-b-2 border-ink pb-2">
        <h2 id="open-drives" className="font-display text-xl font-semibold">
          Open drives right now
        </h2>
        <Link to="/events" className="text-sm font-semibold text-navy hover:underline">See all</Link>
      </div>
      <div className="card mt-0 divide-y divide-ink/10 overflow-hidden rounded-t-none">
        {loading && [0, 1, 2].map((i) => <RosterRowSkeleton key={i} />)}
        {!loading && error && <div className="p-4"><ErrorAlert message={error} onRetry={reload} /></div>}
        {!loading && !error && drives.length === 0 && <p className="p-4 text-sm text-ink/50">No open drives yet. Check back soon.</p>}
        {drives.map((event) => <EventCard key={event.id} event={event} />)}
      </div>
    </section>
  )
}

export default function Landing() {
  return (
    <div className="pb-20 sm:pb-0">
      <section className="mx-auto max-w-3xl px-4 py-12 sm:py-20">
        <div className="flex flex-col-reverse items-start gap-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-xl">
            <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
              NGOs, NSS units and students on one register.
            </h1>
            <p className="mt-4 max-w-md text-base text-ink/70">
              Find a verified drive, check in with a QR code, and walk away with hours and a certificate that hold up.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link to="/register" className="btn-primary px-6 py-3 text-base">Create your free account</Link>
              <Link to="/events" className="text-sm font-semibold text-navy hover:underline">Browse open drives</Link>
            </div>
          </div>

          {/* The stamp: NSS's real motto, rendered once as a physical ink-stamp moment
              rather than a text eyebrow label — the one deliberate motion on this page. */}
          <div className="stamp shrink-0 self-center sm:self-auto" aria-hidden="true">
            <div className="grid h-28 w-28 rotate-[-8deg] place-items-center rounded-full border-[3px] border-flag text-center text-flag sm:h-32 sm:w-32">
              <span className="font-display text-[11px] font-bold uppercase leading-tight tracking-wide">
                Not Me<br />But You
              </span>
            </div>
          </div>
        </div>
      </section>

      <OpenDrives />

      <section aria-labelledby="how-it-works" className="mx-auto max-w-3xl px-4 py-10">
        <h2 id="how-it-works" className="border-b-2 border-ink pb-2 font-display text-xl font-semibold">How it works</h2>
        {/* A real 3-step sequence, so it keeps its numbers — styled as ticket stubs
            (a keepsake shape with a notch) to echo the certificate you end up with. */}
        <ol className="mt-6 grid gap-px sm:grid-cols-3">
          {STEPS.map(([n, title, text]) => (
            <li key={n} className="ticket flex flex-col gap-2 p-5">
              <span className="font-display text-2xl font-bold text-navy">{n}</span>
              <h3 className="font-semibold text-ink">{title}</h3>
              <p className="text-sm text-ink/60">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="faq" className="mx-auto max-w-2xl px-4 py-10">
        <h2 id="faq" className="border-b-2 border-ink pb-2 font-display text-xl font-semibold">Frequently asked questions</h2>
        <div className="mt-4 divide-y divide-ink/10">
          {FAQS.map(([q, a]) => (
            <details key={q} className="group py-3">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 font-medium text-ink marker:hidden [&::-webkit-details-marker]:hidden">
                {q}
                <span aria-hidden="true" className="text-navy transition-transform group-open:rotate-180">⌄</span>
              </summary>
              <p className="mt-2 text-sm text-ink/60">{a}</p>
            </details>
          ))}
        </div>
        <div className="mt-8">
          <Link to="/register" className="btn-primary px-6 py-3 text-base">Create your free account</Link>
        </div>
      </section>

      {/* Sticky CTA – mobile only, stays visible while scrolling */}
      <div className="fixed inset-x-0 bottom-0 z-[900] border-t border-ink/10 bg-paper/95 p-3 backdrop-blur sm:hidden">
        <Link to="/register" className="btn-primary w-full">Create your free account</Link>
      </div>
    </div>
  )
}
