import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import applicationService from '../services/applicationService'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { formatDateTime } from '../utils/format'
import { EmptyState, ErrorAlert, PageHeader, Spinner, StatusBadge, Tabs } from '../components/ui'

export default function EventApplications() {
  const { id } = useParams()
  const toast = useToast()
  const [status, setStatus] = useState('')
  const { data, loading, error, reload } = useAsync(() => applicationService.forEvent(id, status ? { status } : {}), [id, status])
  const groups = useAsync(() => eventService.groupApplications(id), [id])
  const [busyId, setBusyId] = useState(null)

  const decide = async (appId, fn, label) => {
    setBusyId(appId)
    try {
      await fn(appId)
      toast(label)
      await reload()
    } catch (e) {
      toast(errorMessage(e), 'error')
    } finally {
      setBusyId(null)
    }
  }
  const decideGroup = async (gaId, decision) => {
    try {
      await eventService.decideGroup(gaId, decision)
      toast(`Group application ${decision}ed`)
      groups.reload()
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }

  if (loading && !data) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const ev = data.event
  const c = data.counts
  return (
    <div>
      <Link to={`/events/${id}`} className="text-sm text-brand-700">← {ev.title}</Link>
      <PageHeader title="Applications" subtitle={`${ev.approved_count}/${ev.maximum_volunteers} confirmed · ${ev.spots_left} spots left`} actions={<Link to={`/events/${id}/attendance`} className="btn-secondary">QR & attendance →</Link>} />
      <Tabs
        value={status}
        onChange={setStatus}
        tabs={[{ value: '', label: 'All' }, ...['PENDING', 'APPROVED', 'WAITLISTED', 'REJECTED', 'CANCELLED', 'COMPLETED'].map((s) => ({ value: s, label: `${s[0]}${s.slice(1).toLowerCase()} (${c[s]})` }))]}
      />
      {data.results.length === 0 ? (
        <EmptyState title="No applications here yet" />
      ) : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead><tr><th>Volunteer</th><th>College / Unit</th><th>Contact</th><th>Skills</th><th>Applied</th><th>Status</th><th className="text-right">Actions</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {data.results.map((a) => (
                <tr key={a.id}>
                  <td className="font-medium">{a.volunteer_name}{a.motivation && <p className="max-w-xs text-xs font-normal text-slate-500">“{a.motivation}”</p>}</td>
                  <td className="text-xs">{a.college_name || '—'}<br /><span className="text-slate-500">{a.nss_unit_name}</span></td>
                  <td className="text-xs">{a.email}<br />{a.phone}</td>
                  <td className="text-xs">{a.skills.join(', ') || '—'}</td>
                  <td className="whitespace-nowrap text-xs">{formatDateTime(a.application_date)}</td>
                  <td><StatusBadge status={a.status} />{a.attendance_status && <div className="mt-1"><StatusBadge status={a.attendance_status} /></div>}</td>
                  <td className="whitespace-nowrap text-right">
                    {['PENDING', 'WAITLISTED', 'REJECTED'].includes(a.status) && (
                      <button className="btn-success btn-sm" disabled={busyId === a.id} onClick={() => decide(a.id, applicationService.approve, 'Approved – volunteer notified')}>Approve</button>
                    )}{' '}
                    {['PENDING', 'APPROVED'].includes(a.status) && (
                      <button className="btn-secondary btn-sm" disabled={busyId === a.id} onClick={() => decide(a.id, applicationService.waitlist, 'Waitlisted')}>Waitlist</button>
                    )}{' '}
                    {['PENDING', 'WAITLISTED', 'APPROVED'].includes(a.status) && (
                      <button className="btn-ghost btn-sm text-red-600" disabled={busyId === a.id} onClick={() => decide(a.id, applicationService.reject, 'Rejected')}>Reject</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="mb-3 mt-8 text-lg font-semibold">NSS unit group applications</h2>
      {groups.data?.length ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {groups.data.map((g) => (
            <div key={g.id} className="card p-4">
              <div className="flex items-center justify-between gap-2">
                <Link to={`/nss-units/${g.nss_unit}`} className="font-medium text-brand-700">{g.nss_unit_name}</Link>
                <StatusBadge status={g.status} />
              </div>
              <p className="mt-1 text-sm">Requests <b>{g.requested_volunteer_count}</b> volunteers{g.skills.length > 0 && ` · ${g.skills.join(', ')}`}</p>
              {g.message && <p className="mt-1 text-sm text-slate-600">“{g.message}”</p>}
              <p className="mt-1 text-xs text-slate-500">by {g.submitted_by_name} · {formatDateTime(g.created_at)}</p>
              {g.status === 'PENDING' && (
                <div className="mt-3 flex gap-2">
                  <button className="btn-success btn-sm" onClick={() => decideGroup(g.id, 'accept')}>Accept unit</button>
                  <button className="btn-ghost btn-sm text-red-600" onClick={() => decideGroup(g.id, 'reject')}>Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No group applications. Use “Recommend NSS units” on the drive page to invite well-matched units.</p>
      )}
    </div>
  )
}
