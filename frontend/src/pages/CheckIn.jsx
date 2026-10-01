import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import attendanceService from '../services/attendanceService'
import { extractToken, formatDate, formatDateTime, formatTime } from '../utils/format'
import QRScanner from '../components/QRScanner'
import { ErrorAlert, InfoAlert, PageHeader, Spinner, StatusBadge } from '../components/ui'

/** /attendance/check-in/:token – opened by scanning the event QR with any camera app. */
export function CheckIn() {
  const { token } = useParams()
  const toast = useToast()
  const [state, setState] = useState({ loading: true })
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setState({ loading: false, data: await attendanceService.scanStatus(token) })
    } catch (e) {
      setState({ loading: false, error: errorMessage(e) })
    }
  }, [token])
  useEffect(() => {
    load()
  }, [load])

  const act = async (fn) => {
    setBusy(true)
    try {
      const res = await fn(token)
      toast(res.detail)
      await load()
    } catch (e) {
      toast(errorMessage(e), 'error')
      await load()
    } finally {
      setBusy(false)
    }
  }

  if (state.loading) return <Spinner label="Validating QR code…" />
  if (state.error)
    return (
      <div className="mx-auto max-w-md space-y-4">
        <ErrorAlert message={state.error} />
        <Link to="/scan" className="btn-secondary w-full">Scan again</Link>
      </div>
    )
  const { event, application_status: appStatus, attendance, next_action: next, window: win } = state.data
  return (
    <div className="mx-auto max-w-md">
      <div className="card p-6 text-center">
        <p className="text-xs uppercase tracking-wide text-slate-500">Attendance</p>
        <h1 className="mt-1 text-xl font-bold">{event.title}</h1>
        <p className="text-sm text-slate-500">{formatDate(event.date)} · {formatTime(event.start_time)}–{formatTime(event.end_time)} · {event.location}</p>
        <div className="mt-4 space-y-2 text-sm">
          <p>Your registration: {appStatus ? <StatusBadge status={appStatus} /> : <b>not registered</b>}</p>
          {attendance && (
            <p>
              <StatusBadge status={attendance.status} /> in {formatDateTime(attendance.check_in)}
              {attendance.check_out && <> · out {formatDateTime(attendance.check_out)} · <b>{attendance.hours}h</b></>}
            </p>
          )}
        </div>
        <div className="mt-6">
          {next === 'check_in' && (
            <>
              <button className="btn-primary w-full py-3 text-base" disabled={busy} onClick={() => act(attendanceService.checkIn)}>✅ Check in now</button>
              <p className="mt-2 text-xs text-slate-500">Check-in opens {formatDateTime(win.opens)} · on time until {formatDateTime(new Date(new Date(win.starts).getTime() + 15 * 60000))}</p>
            </>
          )}
          {next === 'check_out' && <button className="btn-primary w-full py-3 text-base" disabled={busy} onClick={() => act(attendanceService.checkOut)}>👋 Check out</button>}
          {next === 'feedback' && (
            <>
              <InfoAlert tone="warn">You're checked out. Submit feedback to verify your hours and get your certificate.</InfoAlert>
              <Link to={`/events/${event.id}`} className="btn-primary mt-3 w-full">Give feedback</Link>
            </>
          )}
          {next === 'done' && <InfoAlert tone="success">All done — hours verified and certificate issued. 🎉 <Link to="/certificates" className="font-semibold underline">View certificates</Link></InfoAlert>}
        </div>
      </div>
    </div>
  )
}

/** /scan – in-app camera scanner. */
export function Scan() {
  const navigate = useNavigate()
  const [manual, setManual] = useState('')
  const [error, setError] = useState(null)
  const onScan = useCallback(
    (text) => {
      const token = extractToken(text)
      if (token) navigate(`/attendance/check-in/${token}`)
      else setError('That QR code is not an NSS Connect attendance code.')
    },
    [navigate],
  )
  return (
    <div className="mx-auto max-w-md">
      <PageHeader title="Scan event QR" subtitle="Point your camera at the QR code displayed by the organizer." />
      <QRScanner onScan={onScan} />
      <ErrorAlert message={error} />
      <form className="mt-6 flex gap-2" onSubmit={(e) => { e.preventDefault(); onScan(manual) }}>
        <input className="input" placeholder="…or paste the check-in link" value={manual} onChange={(e) => setManual(e.target.value)} />
        <button className="btn-secondary">Go</button>
      </form>
    </div>
  )
}
