import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import attendanceService from '../services/attendanceService'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { formatDateTime } from '../utils/format'
import { ErrorAlert, InfoAlert, PageHeader, Spinner, StatCard, StatusBadge } from '../components/ui'

export default function EventAttendance() {
  const { id } = useParams()
  const toast = useToast()
  const event = useAsync(() => eventService.get(id), [id])
  const { data, loading, error, reload } = useAsync(() => attendanceService.forEvent(id), [id])
  const feedback = useAsync(() => attendanceService.feedback(id), [id])
  const [qr, setQr] = useState(null)
  const [qrError, setQrError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [big, setBig] = useState(false)

  useEffect(() => {
    attendanceService.currentQR(id).then(setQr).catch(() => setQr(null))
  }, [id])
  // live refresh while the QR is displayed at the venue
  useEffect(() => {
    if (!qr) return undefined
    const t = setInterval(reload, 15000)
    return () => clearInterval(t)
  }, [qr, reload])

  const generate = async () => {
    setQrError(null)
    try {
      setQr(await attendanceService.generateQR(id))
      toast('New QR generated – earlier codes are now invalid')
    } catch (e) {
      setQrError(errorMessage(e))
    }
  }
  const run = async (fn, msg) => {
    setBusy(true)
    try {
      const r = await fn()
      toast(typeof msg === 'function' ? msg(r) : msg)
      await Promise.all([reload(), event.reload()])
    } catch (e) {
      toast(errorMessage(e), 'error')
    } finally {
      setBusy(false)
    }
  }

  if ((loading && !data) || event.loading) return <Spinner />
  if (error || event.error) return <ErrorAlert message={error || event.error} onRetry={reload} />
  const ev = event.data
  const s = data.summary
  const active = ['APPROVED', 'ONGOING'].includes(ev.status)

  return (
    <div>
      <Link to={`/events/${id}`} className="text-sm text-brand-700">← {ev.title}</Link>
      <PageHeader title="QR attendance" subtitle="Volunteers scan this code at the venue to check in, and again to check out. All validation happens on the server." />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card p-5 text-center">
          {qr ? (
            <>
              <img src={qr.qr_image} alt="Attendance QR code" className="mx-auto w-full max-w-xs rounded-xl ring-1 ring-slate-200" />
              <p className="mt-2 break-all text-[11px] text-slate-500">{qr.check_in_url}</p>
              <p className="text-xs text-slate-500">Valid until {formatDateTime(qr.expires_at)}</p>
              <div className="mt-3 flex flex-wrap justify-center gap-2">
                <button className="btn-secondary btn-sm" onClick={() => setBig(true)}>Full screen</button>
                {active && <button className="btn-secondary btn-sm" onClick={generate}>Rotate code</button>}
              </div>
            </>
          ) : active ? (
            <>
              <p className="mb-3 text-sm text-slate-600">No active QR code for this drive.</p>
              <button className="btn-primary" onClick={generate}>Generate attendance QR</button>
            </>
          ) : (
            <InfoAlert>QR codes are available only while the drive is approved or ongoing (current: {ev.status.toLowerCase()}).</InfoAlert>
          )}
          <ErrorAlert message={qrError} />
          {big && qr && (
            <div className="fixed inset-0 z-[1600] flex flex-col items-center justify-center gap-4 bg-white p-6" onClick={() => setBig(false)}>
              <h2 className="text-2xl font-bold">{ev.title}</h2>
              <img src={qr.qr_image} alt="Attendance QR code" className="w-full max-w-[80vh]" />
              <p className="text-sm text-slate-500">Scan to check in / check out · tap anywhere to close</p>
            </div>
          )}
          {qr && !window.location.protocol.startsWith('https') && !['localhost', '127.0.0.1'].includes(window.location.hostname) && (
            <p className="mt-3 text-xs text-amber-700">Tip: phones need HTTPS for the in-app camera scanner. Open NSS Connect via your tunnel URL — the phone's own camera app also works with this QR.</p>
          )}
        </section>
        <div className="space-y-6 lg:col-span-2">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Approved" value={s.approved} />
            <StatCard label="Present" value={s.present} hint={`${s.late} late`} />
            <StatCard label="Absent" value={s.absent} />
            <StatCard label="Hours logged" value={s.total_hours} hint={`${s.feedback_count} feedback`} />
          </div>
          <div className="flex flex-wrap gap-2">
            {active && <button className="btn-success" disabled={busy} onClick={() => window.confirm('Complete this drive now?') && run(() => eventService.setStatus(id, 'COMPLETED'), (r) => `Drive completed · ${r.close_out.auto_checked_out} auto checked-out · ${r.close_out.marked_absent} marked absent`)}>✔ Complete drive & close out</button>}
            <button className="btn-secondary" disabled={busy} onClick={() => run(() => attendanceService.markAbsent(id), (r) => `${r.marked_absent} marked absent`)}>Mark no-shows absent</button>
            <button className="btn-ghost" onClick={reload}>↻ Refresh</button>
          </div>
          <section className="card overflow-x-auto">
            <table className="table">
              <thead><tr><th>Volunteer</th><th>Status</th><th>Check-in</th><th>Check-out</th><th>Hours</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {data.records.map((r) => (
                  <tr key={r.id}>
                    <td className="font-medium">{r.volunteer_name}<div className="text-xs font-normal text-slate-500">{r.volunteer_email}</div></td>
                    <td><StatusBadge status={r.status} /></td>
                    <td className="whitespace-nowrap text-xs">{formatDateTime(r.check_in)}</td>
                    <td className="whitespace-nowrap text-xs">{formatDateTime(r.check_out)}</td>
                    <td className="text-xs">{r.hours ?? '—'} {r.hours != null && (r.hours_verified ? '✓' : '(feedback pending)')}</td>
                  </tr>
                ))}
                {data.not_checked_in.map((n) => (
                  <tr key={`n-${n.volunteer}`} className="bg-slate-50/60">
                    <td className="font-medium">{n.name}<div className="text-xs font-normal text-slate-500">{n.email}</div></td>
                    <td colSpan={4} className="text-xs text-slate-500">Approved · not checked in yet</td>
                  </tr>
                ))}
                {data.records.length + data.not_checked_in.length === 0 && (
                  <tr><td colSpan={5} className="py-6 text-center text-slate-500">No approved volunteers yet.</td></tr>
                )}
              </tbody>
            </table>
          </section>
          {feedback.data?.count > 0 && (
            <section className="card p-5">
              <h2 className="mb-2 font-semibold">Feedback · average {Number(feedback.data.average_rating).toFixed(1)}/5</h2>
              <ul className="space-y-2 text-sm">
                {feedback.data.results.map((f) => (
                  <li key={f.id}><span className="text-amber-500">{'★'.repeat(f.rating)}</span> <b>{f.volunteer_name}</b> {f.comments && `— ${f.comments}`}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
