import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import adminService from '../../services/adminService'
import analyticsService from '../../services/analyticsService'
import applicationService from '../../services/applicationService'
import attendanceService from '../../services/attendanceService'
import certificateService from '../../services/certificateService'
import eventService from '../../services/eventService'
import ngoService from '../../services/ngoService'
import nssService from '../../services/nssService'
import useAsync from '../../utils/useAsync'
import { CATEGORIES, ROLES } from '../../utils/constants'
import { formatDate, formatDateTime } from '../../utils/format'
import { CategoryBadge, EmptyState, ErrorAlert, Pagination, Spinner, StatCard, StatusBadge, Tabs } from '../../components/ui'

const LINKS = [
  ['/admin', 'Overview', true],
  ['/admin/users', 'Users'],
  ['/admin/ngos', 'NGOs'],
  ['/admin/nss-units', 'NSS Units'],
  ['/admin/events', 'Events'],
  ['/admin/applications', 'Applications'],
  ['/admin/attendance', 'Attendance'],
  ['/admin/certificates', 'Certificates'],
  ['/admin/reports', 'Reports'],
]

export function AdminLayout() {
  const { user } = useAuth()
  return (
    <div>
      <div className="mb-6 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="page-title">Admin panel</h1>
          <p className="text-sm text-slate-500">
            {ROLES[user.role]}
            {user.organization && ` · scope: ${user.organization.name}`} · every action is permission-checked on the server
          </p>
        </div>
        <a href="/django-admin/" className="text-xs text-slate-500 hover:text-brand-700">Django admin ↗</a>
      </div>
      <nav className="mb-6 flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
        {LINKS.map(([to, label, end]) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-navy'}`}>
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}

function useAction(reload) {
  const toast = useToast()
  const [busy, setBusy] = useState(null)
  const run = async (key, fn, msg) => {
    setBusy(key)
    try {
      await fn()
      toast(msg)
      await reload()
    } catch (e) {
      toast(errorMessage(e), 'error')
    } finally {
      setBusy(null)
    }
  }
  return [busy, run]
}

function Table({ head, children, empty }) {
  return (
    <div className="card overflow-x-auto">
      <table className="table">
        <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
      {empty && <p className="py-8 text-center text-sm text-slate-500">{empty}</p>}
    </div>
  )
}

// ---------------------------------------------------------------- overview
export function AdminHome() {
  const { data, loading, error, reload } = useAsync(() => analyticsService.adminDashboard(), [])
  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const p = data.pending
  const t = data.totals
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {p.ngos != null && <Link to="/admin/ngos?status=PENDING"><StatCard label="NGOs pending" value={p.ngos} icon="🏢" /></Link>}
        <Link to="/admin/nss-units?status=PENDING"><StatCard label="NSS units pending" value={p.nss_units} icon="🎓" /></Link>
        <Link to="/admin/events"><StatCard label="Drives pending" value={p.events} icon="📋" /></Link>
        <Link to="/admin/applications"><StatCard label="Applications pending" value={p.applications} icon="📝" /></Link>
        <Link to="/admin/users"><StatCard label="Users" value={t.users} hint={`${t.suspended_users} suspended`} icon="👥" /></Link>
        <StatCard label="Verified NGOs" value={t.ngos_verified} icon="✓" />
        <StatCard label="Verified NSS units" value={t.nss_units_verified} icon="✓" />
        <Link to="/admin/certificates"><StatCard label="Certificates" value={t.certificates} icon="📜" /></Link>
      </div>
      <section className="card p-5">
        <h2 className="mb-3 font-semibold">Recently created drives</h2>
        <ul className="divide-y divide-slate-100 text-sm">
          {data.recent_events.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-2 py-2">
              <Link to={`/events/${e.id}`} className="font-medium hover:text-brand-700">{e.title}</Link>
              <span className="flex items-center gap-2"><CategoryBadge category={e.category} /><StatusBadge status={e.status} /></span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

// ---------------------------------------------------------------- users
export function AdminUsers() {
  const { user: me, isSuperAdmin } = useAuth()
  const [role, setRole] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => adminService.users({ role: role || undefined, search: search || undefined, page }), [role, search, page])
  const [busy, run] = useAction(reload)
  return (
    <div>
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input className="input sm:max-w-xs" placeholder="Search name or email…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
        <select className="input sm:max-w-xs" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}>
          <option value="">All roles</option>
          {Object.entries(ROLES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['User', 'Role', 'Organization', 'Joined', 'Status', 'Actions']} empty={data.results.length ? null : 'No users found.'}>
          {data.results.map((u) => (
            <tr key={u.id}>
              <td><p className="font-medium">{u.full_name}</p><p className="text-xs text-slate-500">{u.email}{!u.is_email_verified && ' · unverified email'}</p></td>
              <td>
                {isSuperAdmin && u.id !== me.id ? (
                  <select className="input py-1 text-xs" value={u.role} disabled={busy === u.id} onChange={(e) => run(u.id, () => adminService.updateUser(u.id, { role: e.target.value }), 'Role updated')}>
                    {Object.entries(ROLES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                ) : ROLES[u.role]}
              </td>
              <td className="text-xs">{u.organization?.name || '—'}</td>
              <td className="whitespace-nowrap text-xs">{formatDate(u.date_joined)}</td>
              <td>{u.is_active ? <span className="badge bg-green-50 text-green-700 ring-green-200">Active</span> : <StatusBadge status="SUSPENDED" />}</td>
              <td className="whitespace-nowrap">
                {u.id !== me.id && (u.is_active ? (
                  <button className="btn-ghost btn-sm text-red-600" disabled={busy === u.id} onClick={() => window.confirm(`Suspend ${u.email}? They will be logged out everywhere.`) && run(u.id, () => adminService.suspend(u.id), 'Account suspended')}>Suspend</button>
                ) : (
                  <button className="btn-secondary btn-sm" disabled={busy === u.id} onClick={() => run(u.id, () => adminService.activate(u.id), 'Account re-activated')}>Activate</button>
                ))}
              </td>
            </tr>
          ))}
        </Table>
      )}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

// ---------------------------------------------------------------- NGOs
export function AdminNgos() {
  const { permissions } = useAuth()
  const [status, setStatus] = useState(new URLSearchParams(window.location.search).get('status') || '')
  const { data, loading, error, reload } = useAsync(() => ngoService.list({ status: status || undefined, page_size: 100 }), [status])
  const [busy, run] = useAction(reload)
  const act = (n, fn, label) => {
    const note = label === 'verified' ? '' : window.prompt(`Reason (sent to the NGO):`)
    if (note === null) return
    run(n.id, () => fn(n.id, note), `NGO ${label}`)
  }
  return (
    <div>
      <Tabs value={status} onChange={setStatus} tabs={[{ value: '', label: 'All' }, ...['PENDING', 'VERIFIED', 'REJECTED', 'SUSPENDED'].map((s) => ({ value: s, label: s[0] + s.slice(1).toLowerCase() }))]} />
      {!permissions.reviewNgos && <p className="mb-3 text-sm text-amber-700">NGO verification is done by university and super admins.</p>}
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['NGO', 'Owner', 'Focus', 'Registered', 'Status', 'Actions']} empty={data.results.length ? null : 'No NGOs.'}>
          {data.results.map((n) => (
            <tr key={n.id}>
              <td><Link to={`/ngos/${n.id}`} className="font-medium text-brand-700">{n.name}</Link><p className="text-xs text-slate-500">{n.location}</p></td>
              <td className="text-xs">{n.owner_name || '—'}<br />{n.email}</td>
              <td className="text-xs">{n.focus_areas.join(', ')}</td>
              <td className="whitespace-nowrap text-xs">{formatDate(n.created_at)}</td>
              <td><StatusBadge status={n.verification_status} /></td>
              <td className="whitespace-nowrap">
                <Link to={`/ngos/${n.id}`} className="btn-ghost btn-sm">Documents</Link>
                {permissions.reviewNgos && n.verification_status !== 'VERIFIED' && <button className="btn-success btn-sm" disabled={busy === n.id} onClick={() => act(n, ngoService.verify, 'verified')}>Verify</button>}{' '}
                {permissions.reviewNgos && n.verification_status === 'PENDING' && <button className="btn-ghost btn-sm text-red-600" disabled={busy === n.id} onClick={() => act(n, ngoService.reject, 'rejected')}>Reject</button>}
                {permissions.reviewNgos && n.verification_status === 'VERIFIED' && <button className="btn-ghost btn-sm text-red-600" disabled={busy === n.id} onClick={() => act(n, ngoService.suspend, 'suspended')}>Suspend</button>}
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- NSS units
export function AdminNssUnits() {
  const [status, setStatus] = useState(new URLSearchParams(window.location.search).get('status') || '')
  const { data, loading, error, reload } = useAsync(() => nssService.list({ status: status || undefined, page_size: 100 }), [status])
  const [busy, run] = useAction(reload)
  return (
    <div>
      <Tabs value={status} onChange={setStatus} tabs={[{ value: '', label: 'All' }, ...['PENDING', 'VERIFIED', 'REJECTED', 'SUSPENDED'].map((s) => ({ value: s, label: s[0] + s.slice(1).toLowerCase() }))]} />
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['Unit', 'University', 'Coordinator', 'Volunteers', 'Status', 'Actions']} empty={data.results.length ? null : 'No NSS units.'}>
          {data.results.map((u) => (
            <tr key={u.id}>
              <td><Link to={`/nss-units/${u.id}`} className="font-medium text-brand-700">{u.display_name}</Link></td>
              <td className="text-xs">{u.university_name}</td>
              <td className="text-xs">{u.coordinator_name || '—'}</td>
              <td>{u.volunteer_count}</td>
              <td><StatusBadge status={u.verification_status} /></td>
              <td className="whitespace-nowrap">
                {u.verification_status !== 'VERIFIED' && <button className="btn-success btn-sm" disabled={busy === u.id} onClick={() => run(u.id, () => nssService.verify(u.id), 'Unit verified')}>Verify</button>}{' '}
                {u.verification_status === 'PENDING' && <button className="btn-ghost btn-sm text-red-600" disabled={busy === u.id} onClick={() => run(u.id, () => nssService.reject(u.id), 'Unit rejected')}>Reject</button>}
                {u.verification_status === 'VERIFIED' && <button className="btn-ghost btn-sm text-red-600" disabled={busy === u.id} onClick={() => run(u.id, () => nssService.suspend(u.id), 'Unit suspended')}>Suspend</button>}
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- events
export function AdminEvents() {
  const [status, setStatus] = useState('PENDING')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(
    () => eventService.list({ status: status || undefined, all: 'true', category: category || undefined, page, ordering: '-date' }),
    [status, category, page],
  )
  const [busy, run] = useAction(reload)
  return (
    <div>
      <Tabs value={status} onChange={(v) => { setStatus(v); setPage(1) }} tabs={[{ value: '', label: 'All' }, ...['PENDING', 'APPROVED', 'ONGOING', 'COMPLETED', 'REJECTED', 'CANCELLED'].map((s) => ({ value: s, label: s[0] + s.slice(1).toLowerCase() }))]} />
      <select className="input mb-4 max-w-xs" value={category} onChange={(e) => setCategory(e.target.value)}>
        <option value="">All categories</option>
        {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['Drive', 'Category', 'Date', 'Organizer', 'Volunteers', 'Status', 'Actions']} empty={data.results.length ? null : 'No drives in this view.'}>
          {data.results.map((e) => (
            <tr key={e.id}>
              <td><Link to={`/events/${e.id}`} className="font-medium text-brand-700">{e.title}</Link><p className="text-xs text-slate-500">{e.location}</p></td>
              <td><CategoryBadge category={e.category} /></td>
              <td className="whitespace-nowrap text-xs">{formatDate(e.date)}</td>
              <td className="text-xs">{e.organizer_display}</td>
              <td className="text-xs">{e.approved_count}/{e.maximum_volunteers}</td>
              <td><StatusBadge status={e.status} /></td>
              <td className="whitespace-nowrap">
                {['PENDING', 'REJECTED'].includes(e.status) && <button className="btn-success btn-sm" disabled={busy === e.id} onClick={() => run(e.id, () => eventService.approve(e.id), 'Drive approved')}>Approve</button>}{' '}
                {e.status === 'PENDING' && (
                  <button className="btn-ghost btn-sm text-red-600" disabled={busy === e.id} onClick={() => { const note = window.prompt('Reason for rejection:'); if (note !== null) run(e.id, () => eventService.reject(e.id, note), 'Drive rejected') }}>Reject</button>
                )}
              </td>
            </tr>
          ))}
        </Table>
      )}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

// ---------------------------------------------------------------- applications
export function AdminApplications() {
  const [status, setStatus] = useState('PENDING')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => applicationService.list({ status: status || undefined, search: search || undefined, page }), [status, search, page])
  const [busy, run] = useAction(reload)
  return (
    <div>
      <Tabs value={status} onChange={(v) => { setStatus(v); setPage(1) }} tabs={[{ value: '', label: 'All' }, ...['PENDING', 'APPROVED', 'WAITLISTED', 'REJECTED', 'CANCELLED', 'COMPLETED'].map((s) => ({ value: s, label: s[0] + s.slice(1).toLowerCase() }))]} />
      <input className="input mb-4 max-w-xs" placeholder="Search volunteer or drive…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['Volunteer', 'Drive', 'College', 'Applied', 'Status', 'Actions']} empty={data.results.length ? null : 'No applications.'}>
          {data.results.map((a) => (
            <tr key={a.id}>
              <td className="font-medium">{a.volunteer_name}<p className="text-xs font-normal text-slate-500">{a.email}</p></td>
              <td><Link to={`/events/${a.event}/applications`} className="text-brand-700">{a.event_title}</Link><p className="text-xs text-slate-500">{formatDate(a.event_date)}</p></td>
              <td className="text-xs">{a.college_name || '—'}</td>
              <td className="whitespace-nowrap text-xs">{formatDateTime(a.application_date)}</td>
              <td><StatusBadge status={a.status} /></td>
              <td className="whitespace-nowrap">
                {['PENDING', 'WAITLISTED'].includes(a.status) && <button className="btn-success btn-sm" disabled={busy === a.id} onClick={() => run(a.id, () => applicationService.approve(a.id), 'Approved')}>Approve</button>}{' '}
                {['PENDING', 'WAITLISTED', 'APPROVED'].includes(a.status) && <button className="btn-ghost btn-sm text-red-600" disabled={busy === a.id} onClick={() => run(a.id, () => applicationService.reject(a.id), 'Rejected')}>Reject</button>}
              </td>
            </tr>
          ))}
        </Table>
      )}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

// ---------------------------------------------------------------- attendance
export function AdminAttendance() {
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => attendanceService.list({ status: status || undefined, search: search || undefined, page }), [status, search, page])
  return (
    <div>
      <Tabs value={status} onChange={(v) => { setStatus(v); setPage(1) }} tabs={[{ value: '', label: 'All' }, { value: 'PRESENT', label: 'Present' }, { value: 'LATE', label: 'Late' }, { value: 'ABSENT', label: 'Absent' }]} />
      <input className="input mb-4 max-w-xs" placeholder="Search volunteer or drive…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['Volunteer', 'Drive', 'Status', 'Check-in', 'Check-out', 'Hours']} empty={data.results.length ? null : 'No attendance records.'}>
          {data.results.map((r) => (
            <tr key={r.id}>
              <td className="font-medium">{r.volunteer_name}<p className="text-xs font-normal text-slate-500">{r.volunteer_email}</p></td>
              <td><Link to={`/events/${r.event}/attendance`} className="text-brand-700">{r.event_title}</Link><p className="text-xs text-slate-500">{formatDate(r.event_date)}</p></td>
              <td><StatusBadge status={r.status} /></td>
              <td className="whitespace-nowrap text-xs">{formatDateTime(r.check_in)}</td>
              <td className="whitespace-nowrap text-xs">{formatDateTime(r.check_out)}</td>
              <td className="text-xs">{r.hours ?? '—'} {r.hours != null && (r.hours_verified ? '✓' : '(unverified)')}</td>
            </tr>
          ))}
        </Table>
      )}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

// ---------------------------------------------------------------- certificates
export function AdminCertificates() {
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => certificateService.list({ search: search || undefined, page }), [search, page])
  const [busy, run] = useAction(reload)
  return (
    <div>
      <input className="input mb-4 max-w-xs" placeholder="Search ID, volunteer, drive…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <Table head={['Certificate', 'Volunteer', 'Drive', 'Hours', 'Issued', 'Actions']} empty={data.results.length ? null : 'No certificates.'}>
          {data.results.map((c) => (
            <tr key={c.id}>
              <td className="font-mono text-xs"><Link to={`/certificate/${c.certificate_id}/verify`} className="text-brand-700">{c.certificate_id}</Link>{c.revoked && <StatusBadge status="REJECTED" />}</td>
              <td>{c.volunteer_name}</td>
              <td className="text-xs">{c.event_title}</td>
              <td>{Number(c.hours).toFixed(2)}</td>
              <td className="whitespace-nowrap text-xs">{formatDate(c.issued_at)}</td>
              <td className="whitespace-nowrap">
                <button className="btn-ghost btn-sm" onClick={() => certificateService.download(c).catch((e) => toast(errorMessage(e), 'error'))}>PDF</button>
                <button className="btn-ghost btn-sm text-red-600" disabled={busy === c.id} onClick={() => run(c.id, () => certificateService.revoke(c.id, !c.revoked), c.revoked ? 'Certificate restored' : 'Certificate revoked')}>{c.revoked ? 'Restore' : 'Revoke'}</button>
              </td>
            </tr>
          ))}
        </Table>
      )}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

// ---------------------------------------------------------------- reports
export function AdminReports() {
  const toast = useToast()
  const types = useAsync(() => analyticsService.reportTypes(), [])
  const [type, setType] = useState('event_participation')
  const [range, setRange] = useState({ date_from: '', date_to: '' })
  const params = Object.fromEntries(Object.entries(range).filter(([, v]) => v))
  const preview = useAsync(() => analyticsService.reportPreview(type, params), [type, JSON.stringify(params)])
  const exportAs = async (fmt) => {
    try {
      await analyticsService.exportReport(type, fmt, params)
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  return (
    <div className="space-y-4">
      <div className="card grid gap-3 p-4 sm:grid-cols-4">
        <select className="input sm:col-span-2" value={type} onChange={(e) => setType(e.target.value)}>
          {(types.data || []).map((t) => <option key={t.type} value={t.type}>{t.label}</option>)}
        </select>
        <input type="date" className="input" value={range.date_from} onChange={(e) => setRange({ ...range, date_from: e.target.value })} aria-label="From" />
        <input type="date" className="input" value={range.date_to} onChange={(e) => setRange({ ...range, date_to: e.target.value })} aria-label="To" />
        <div className="flex gap-2 sm:col-span-4">
          <button className="btn-primary" onClick={() => exportAs('csv')}>⬇ Export CSV</button>
          <button className="btn-secondary" onClick={() => exportAs('pdf')}>⬇ Export PDF</button>
        </div>
      </div>
      {preview.loading && <Spinner />}
      <ErrorAlert message={preview.error} />
      {preview.data && (
        preview.data.rows.length ? (
          <Table head={preview.data.headers}>
            {preview.data.rows.slice(0, 100).map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="whitespace-nowrap text-xs">{String(c)}</td>)}</tr>)}
          </Table>
        ) : <EmptyState title="No rows for this report and date range" />
      )}
      {preview.data?.rows.length > 100 && <p className="text-xs text-slate-500">Showing the first 100 of {preview.data.rows.length} rows. Export for the full report.</p>}
    </div>
  )
}
