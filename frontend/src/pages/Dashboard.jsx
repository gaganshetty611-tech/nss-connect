import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAuth } from '../context/AuthContext'
import analyticsService from '../services/analyticsService'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { CATEGORY_COLORS, CATEGORY_LABEL } from '../utils/constants'
import { formatDate, formatTime } from '../utils/format'
import { CategoryBadge, EmptyState, ErrorAlert, InfoAlert, PageHeader, Spinner, StatCard, StatusBadge } from '../components/ui'

function EmergencyBanner() {
  const { data } = useAsync(() => eventService.emergencyList({ active: true, page_size: 3 }), [])
  const items = data?.results || []
  if (!items.length) return null
  return (
    <div className="mb-6 space-y-2">
      {items.map((r) => (
        <div key={r.id} className="flex flex-col gap-1 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200 sm:flex-row sm:items-center sm:justify-between">
          <span>
            <b>🚨 {r.priority}: {r.title}</b> — {r.required_volunteers} volunteers needed at {r.location}.
          </span>
          {r.event && <Link to={`/events/${r.event}`} className="btn-danger btn-sm">View drive</Link>}
        </div>
      ))}
    </div>
  )
}

function VolunteerDashboard() {
  const { data, loading, error, reload } = useAsync(() => analyticsService.volunteerDashboard(), [])
  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const s = data.stats
  const hoursData = Object.entries(s.hours_by_category).map(([k, v]) => ({ name: CATEGORY_LABEL[k], key: k, hours: v }))
  return (
    <>
      <EmergencyBanner />
      {data.pending_feedback.length > 0 && (
        <div className="mb-6">
          <InfoAlert tone="warn">
            <b>Feedback needed:</b> submit post-event feedback to verify your hours and receive certificates for{' '}
            {data.pending_feedback.map((p, i) => (
              <span key={p.event_id}>
                {i > 0 && ', '}
                <Link className="font-semibold underline" to={`/events/${p.event_id}`}>{p.title}</Link> ({p.hours}h)
              </span>
            ))}
            .
          </InfoAlert>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard label="Events Participated" value={s.events_participated} icon="🤝" />
        <StatCard label="Upcoming Drives" value={s.upcoming_drives} icon="📅" hint="Approved registrations" />
        <StatCard label="Registered Events" value={s.registered_events} icon="📝" hint="Pending, approved or waitlisted" />
        <StatCard label="Volunteer Hours" value={s.volunteer_hours} icon="⏱️" hint={s.pending_hours ? `+${s.pending_hours}h awaiting feedback` : 'Verified hours'} />
        <StatCard label="Certificates" value={s.certificates} icon="📜" />
        <StatCard label="Impact Points" value={s.impact_points} icon="⭐" hint={s.impact_points_formula} />
        <StatCard label="Attendance Rate" value={s.attendance_rate == null ? '—' : `${s.attendance_rate}%`} icon="✅" hint={`${s.attendance_total} attendance records`} />
        <StatCard label="Badges" value={`${s.badges.filter((b) => b.earned).length}/${s.badges.length}`} icon="🏅" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="card p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Upcoming & registered drives</h2>
            <Link to="/events" className="text-sm text-brand-700">Explore drives →</Link>
          </div>
          {data.upcoming.length ? (
            <ul className="divide-y divide-slate-100">
              {data.upcoming.map((u) => (
                <li key={u.application_id} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <Link to={`/events/${u.event_id}`} className="font-medium hover:text-brand-700">{u.title}</Link>
                    <p className="text-xs text-slate-500">{formatDate(u.date)} · {formatTime(u.start_time)} · {u.location}</p>
                  </div>
                  <div className="flex gap-2"><CategoryBadge category={u.category} /><StatusBadge status={u.status} /></div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No upcoming registrations yet.</p>
          )}
        </section>
        <section className="card p-5">
          <h2 className="mb-3 font-semibold">Verified hours by category</h2>
          <div className="h-52">
            <ResponsiveContainer>
              <BarChart data={hoursData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={30} />
                <Tooltip />
                <Bar dataKey="hours" radius={[6, 6, 0, 0]}>
                  {hoursData.map((d) => <Cell key={d.key} fill={CATEGORY_COLORS[d.key]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="card p-5 lg:col-span-2">
          <h2 className="font-semibold">Suggested for you</h2>
          <p className="mb-3 text-xs text-slate-500">Rule-based matching on your interests, skills, availability and your unit's distance — a suggestion, not a ranking of worth.</p>
          {data.recommended_events.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {data.recommended_events.map((e) => (
                <Link key={e.id} to={`/events/${e.id}`} className="rounded-xl p-3 ring-1 ring-slate-200 hover:ring-brand-300">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{e.title}</span>
                    <CategoryBadge category={e.category} />
                  </div>
                  <p className="text-xs text-slate-500">{formatDate(e.date)} · {e.location}</p>
                  <ul className="mt-2 space-y-0.5 text-xs text-slate-600">
                    {(e.reasons.length ? e.reasons : ['Open spots available']).map((r) => <li key={r}>• {r}</li>)}
                  </ul>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Add interests and skills to your profile to get suggestions.</p>
          )}
        </section>
        <section className="card p-5">
          <h2 className="mb-3 font-semibold">Badges</h2>
          <div className="grid grid-cols-2 gap-2">
            {s.badges.map((b) => (
              <div key={b.code} title={b.description} className={`rounded-xl p-2 text-center text-xs ring-1 ${b.earned ? 'bg-brand-50 text-brand-800 ring-brand-200' : 'bg-slate-50 text-slate-500 ring-slate-200'}`}>
                <div className="text-lg">{b.earned ? '🏅' : '🔒'}</div>
                <div className="font-semibold">{b.label}</div>
              </div>
            ))}
          </div>
          {data.recent_certificates.length > 0 && (
            <>
              <h3 className="mb-2 mt-5 text-sm font-semibold">Recent certificates</h3>
              <ul className="space-y-1 text-xs">
                {data.recent_certificates.map((c) => (
                  <li key={c.id} className="flex justify-between gap-2">
                    <Link to={`/certificate/${c.certificate_id}/verify`} className="truncate text-brand-700">{c.event}</Link>
                    <span className="shrink-0 text-slate-500">{c.hours}h</span>
                  </li>
                ))}
              </ul>
              <Link to="/certificates" className="mt-2 inline-block text-xs text-brand-700">All certificates →</Link>
            </>
          )}
        </section>
      </div>
    </>
  )
}

function OrganizerDashboard() {
  const { user } = useAuth()
  const { data, loading, error, reload } = useAsync(() => analyticsService.organizerDashboard(), [])
  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const s = data.stats
  const org = data.organization
  return (
    <>
      {!org && user.role === 'NGO_ORGANIZER' && (
        <div className="mb-6"><InfoAlert tone="warn">Register your NGO to start hosting drives. <Link to="/ngos/new" className="font-semibold underline">Register NGO →</Link></InfoAlert></div>
      )}
      {!org && user.role === 'NSS_COORDINATOR' && (
        <div className="mb-6"><InfoAlert tone="warn">Register your NSS unit to host drives and apply as a group. <Link to="/nss-units?new=1" className="font-semibold underline">Register unit →</Link></InfoAlert></div>
      )}
      {org && org.status !== 'VERIFIED' && (
        <div className="mb-6"><InfoAlert tone="warn">{org.name} is <b>{org.status.toLowerCase()}</b>. Drives can be posted once an administrator verifies it.</InfoAlert></div>
      )}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard label="My Drives" value={s.total_events} icon="📋" hint={`${s.events_by_status.APPROVED} approved · ${s.events_by_status.PENDING} pending`} />
        <StatCard label="Pending Applications" value={s.pending_applications} icon="📝" hint={`${s.pending_group_applications} group requests`} />
        <StatCard label="Volunteers Engaged" value={s.unique_volunteers_engaged} icon="🤝" hint={`${s.approved_volunteers} approved registrations`} />
        <StatCard label="Hours Generated" value={s.volunteer_hours_generated} icon="⏱️" hint={s.attendance_rate == null ? 'No attendance yet' : `${s.attendance_rate}% attendance`} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="card p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Upcoming drives</h2>
            <Link to="/events/new" className="btn-primary btn-sm">+ Host drive</Link>
          </div>
          {data.upcoming_events.length ? (
            <div className="overflow-x-auto">
              <table className="table">
                <thead><tr><th>Drive</th><th>Date</th><th>Status</th><th>Approved</th><th>Pending</th><th /></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {data.upcoming_events.map((e) => (
                    <tr key={e.id}>
                      <td><Link to={`/events/${e.id}`} className="font-medium hover:text-brand-700">{e.title}</Link></td>
                      <td className="whitespace-nowrap">{formatDate(e.date)}</td>
                      <td><StatusBadge status={e.status} /></td>
                      <td>{e.approved}/{e.capacity}</td>
                      <td>{e.pending}</td>
                      <td className="whitespace-nowrap text-right">
                        <Link to={`/events/${e.id}/applications`} className="text-brand-700">Applications</Link>
                        {' · '}
                        <Link to={`/events/${e.id}/attendance`} className="text-brand-700">Attendance</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No upcoming drives">Create a drive and it will appear here once approved.</EmptyState>
          )}
        </section>
        <section className="card p-5">
          <h2 className="mb-2 font-semibold">Needs close-out</h2>
          <p className="mb-3 text-xs text-slate-500">Past drives still open. Completing a drive auto-checks-out attendees, marks absentees and writes the summary.</p>
          {data.needs_close_out.length ? (
            <ul className="space-y-2 text-sm">
              {data.needs_close_out.map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-2">
                  <Link to={`/events/${e.id}/attendance`} className="truncate text-brand-700">{e.title}</Link>
                  <span className="shrink-0 text-xs text-slate-500">{formatDate(e.date)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">All caught up ✓</p>
          )}
        </section>
      </div>
    </>
  )
}

function AdminSummary() {
  const { data, loading, error, reload } = useAsync(() => analyticsService.adminDashboard(), [])
  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const p = data.pending
  const t = data.totals
  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        {p.ngos != null && <Link to="/admin/ngos"><StatCard label="NGOs to verify" value={p.ngos} icon="🏢" /></Link>}
        <Link to="/admin/nss-units"><StatCard label="NSS units to verify" value={p.nss_units} icon="🎓" /></Link>
        <Link to="/admin/events"><StatCard label="Drives to approve" value={p.events} icon="📋" /></Link>
        <Link to="/admin/applications"><StatCard label="Pending applications" value={p.applications} icon="📝" /></Link>
        <StatCard label="Users" value={t.users} hint={`${t.volunteers} volunteers · ${t.suspended_users} suspended`} icon="👥" />
        <StatCard label="Drives" value={t.events} icon="📅" />
        <StatCard label="Attendance records" value={t.attendance_records} icon="✅" />
        <StatCard label="Certificates" value={t.certificates} icon="📜" />
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        <Link to="/admin" className="btn-primary">Open admin panel</Link>
        <Link to="/analytics" className="btn-secondary">View analytics</Link>
        <Link to="/admin/reports" className="btn-secondary">Export reports</Link>
      </div>
    </>
  )
}

export default function Dashboard() {
  const { user, isVolunteer, isAdmin } = useAuth()
  return (
    <div>
      <PageHeader
        title={`Hi, ${user.first_name || user.full_name} 👋`}
        subtitle={isVolunteer ? 'Your verified volunteering record, computed live from your attendance.' : isAdmin ? 'Platform overview for your scope.' : 'Manage your drives, applications and attendance.'}
        actions={isVolunteer ? <Link to="/scan" className="btn-primary">📷 Scan event QR</Link> : null}
      />
      {isVolunteer ? <VolunteerDashboard /> : isAdmin ? <AdminSummary /> : <OrganizerDashboard />}
    </div>
  )
}
