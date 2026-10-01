import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import applicationService from '../services/applicationService'
import attendanceService from '../services/attendanceService'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { formatDate, formatDateTime, formatTime } from '../utils/format'
import MapView from '../components/MapView'
import { CategoryBadge, ErrorAlert, Field, InfoAlert, Modal, Spinner, StatusBadge, VerifiedBadge } from '../components/ui'

function Stars({ value, onChange }) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" role="radio" aria-checked={value === n} onClick={() => onChange(n)} className={`text-2xl ${n <= value ? 'text-amber-400' : 'text-slate-300'}`}>
          ★
        </button>
      ))}
    </div>
  )
}

function FeedbackForm({ event, onDone }) {
  const toast = useToast()
  const [rating, setRating] = useState(0)
  const [comments, setComments] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    if (!rating) return setError('Please choose a rating.')
    setBusy(true)
    setError(null)
    try {
      const res = await attendanceService.submitFeedback(event.id, rating, comments)
      toast(res.detail)
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <InfoAlert tone="warn">Feedback is mandatory: your {event.my_attendance.hours} hours are verified and your certificate is issued once you submit it.</InfoAlert>
      <ErrorAlert message={error} />
      <Stars value={rating} onChange={setRating} />
      <textarea className="input" rows={3} placeholder="What went well? What could be better?" value={comments} onChange={(e) => setComments(e.target.value)} maxLength={2000} />
      <button className="btn-primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit feedback'}</button>
    </form>
  )
}

function Gallery({ event }) {
  const { user } = useAuth()
  const toast = useToast()
  const { data, reload } = useAsync(() => eventService.photos(event.id), [event.id])
  const [file, setFile] = useState(null)
  const [caption, setCaption] = useState('')
  const [busy, setBusy] = useState(false)
  const [zoom, setZoom] = useState(null)
  const canUpload = event.can_manage || (event.my_attendance && event.my_attendance.status !== 'ABSENT')
  const getDeviceCoords = () =>
    new Promise((resolve) => {
      // Best-effort only: if geolocation is unsupported, permission is denied, or it
      // times out, resolve with nothing and let the backend fall back to the photo's
      // own EXIF GPS tag instead (see events/views.py EventViewSet.photos). A photo
      // upload should never be blocked on the user granting location access.
      if (!navigator.geolocation) return resolve(null)
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
        () => resolve(null),
        { timeout: 5000, maximumAge: 60000 }
      )
    })

  const upload = async (e) => {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    try {
      const coords = await getDeviceCoords()
      await eventService.uploadPhoto(event.id, file, caption, coords)
      setFile(null)
      setCaption('')
      e.target.reset()
      toast(coords ? 'Photo uploaded with location' : 'Photo uploaded')
      reload()
    } catch (err) {
      toast(errorMessage(err), 'error')
    } finally {
      setBusy(false)
    }
  }
  const remove = async (id) => {
    await eventService.deletePhoto(id)
    reload()
  }
  return (
    <section className="card p-5">
      <h2 className="mb-3 font-semibold">Event gallery</h2>
      {data?.length ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {data.map((p) => (
            <figure key={p.id} className="group relative overflow-hidden rounded-xl">
              <button onClick={() => setZoom(p)} className="block w-full"><img src={p.photo} alt={p.caption || 'Event photo'} className="aspect-square w-full object-cover" loading="lazy" /></button>
              {p.latitude != null && p.longitude != null && (
                <a
                  href={`https://www.openstreetmap.org/?mlat=${p.latitude}&mlon=${p.longitude}#map=17/${p.latitude}/${p.longitude}`}
                  target="_blank"
                  rel="noreferrer"
                  title={p.location_source === 'EXIF' ? 'Location from photo metadata' : "Location from uploader's device"}
                  className="absolute left-1 top-1 rounded bg-white/90 px-1.5 py-0.5 text-xs"
                  onClick={(e) => e.stopPropagation()}
                >
                  📍
                </a>
              )}
              {p.caption && <figcaption className="truncate px-1 py-1 text-xs text-slate-500">{p.caption}</figcaption>}
              {(p.uploaded_by === user?.id || event.can_manage) && (
                <button className="absolute right-1 top-1 hidden rounded bg-white/90 px-1.5 text-xs text-red-600 group-hover:block" onClick={() => remove(p.id)}>Delete</button>
              )}
            </figure>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No photos yet.</p>
      )}
      {canUpload && (
        <form onSubmit={upload} className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" onChange={(e) => setFile(e.target.files[0])} />
          <input className="input" placeholder="Caption (optional)" value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={255} />
          <button className="btn-secondary" disabled={!file || busy}>{busy ? 'Uploading…' : 'Upload'}</button>
        </form>
      )}
      <Modal open={!!zoom} title={zoom?.caption || 'Photo'} onClose={() => setZoom(null)} wide>
        {zoom && <img src={zoom.photo} alt={zoom.caption || 'Event photo'} className="w-full rounded-xl" />}
      </Modal>
    </section>
  )
}

function AIPanel({ event }) {
  const toast = useToast()
  const [tab, setTab] = useState(null)
  const [recs, setRecs] = useState(null)
  const [turnout, setTurnout] = useState(null)
  const [busy, setBusy] = useState(false)
  const [notes, setNotes] = useState(event.organizer_notes || '')
  const [summary, setSummary] = useState(event.summary || '')
  const run = async (which) => {
    setTab(which)
    setBusy(true)
    try {
      if (which === 'recs') setRecs(await eventService.recommendations(event.id))
      if (which === 'turnout') setTurnout(await eventService.turnout(event.id))
    } catch (e) {
      toast(errorMessage(e), 'error')
    } finally {
      setBusy(false)
    }
  }
  const invite = async (unitId) => {
    try {
      const res = await eventService.inviteUnit(event.id, unitId, '', true)
      toast(res.detail)
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  const genSummary = async () => {
    setBusy(true)
    try {
      setSummary((await eventService.summary(event.id, notes)).summary)
      toast('Summary generated')
    } catch (e) {
      toast(errorMessage(e), 'error')
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="card p-5">
      <h2 className="font-semibold">AI assistant <span className="text-xs font-normal text-slate-500">(transparent rule-based scoring)</span></h2>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="btn-secondary btn-sm" onClick={() => run('recs')}>🎯 Recommend NSS units</button>
        <button className="btn-secondary btn-sm" onClick={() => run('turnout')}>📈 Estimate turnout</button>
        <button className="btn-secondary btn-sm" onClick={() => setTab('summary')}>📝 Post-event summary</button>
      </div>
      {busy && <Spinner label="Calculating…" />}
      {tab === 'recs' && recs && !busy && (
        <div className="mt-4 space-y-3">
          <p className="text-xs text-slate-500">{recs.disclaimer}</p>
          {recs.results.length === 0 && <p className="text-sm text-slate-500">No verified NSS units to score yet.</p>}
          {recs.results.map((r, i) => (
            <div key={r.id} className="rounded-xl p-3 ring-1 ring-slate-200">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">#{i + 1} {r.nss_unit_name}</p>
                  <p className="text-xs text-slate-500">{r.volunteer_count} volunteers · {r.available_volunteers} likely available{r.distance_km != null && ` · ${r.distance_km} km`}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-lg bg-brand-50 px-2 py-1 text-sm font-bold text-brand-700">{Number(r.match_score).toFixed(0)}/100</span>
                  <button className="btn-primary btn-sm" onClick={() => invite(r.nss_unit_id)}>Invite</button>
                </div>
              </div>
              <div className="mt-2 grid grid-cols-5 gap-1 text-center text-[10px] text-slate-500">
                {[['Distance', r.distance_score], ['Skills', r.skill_score], ['Availability', r.availability_score], ['Reliability', r.attendance_score], ['Interest', r.interest_score]].map(([k, v]) => (
                  <div key={k}>
                    <div className="h-1.5 rounded-sm bg-ink/10"><div className="h-1.5 rounded-sm bg-navy" style={{ width: `${v}%` }} /></div>
                    {k} {Number(v).toFixed(0)}
                  </div>
                ))}
              </div>
              <ul className="mt-2 space-y-0.5 text-xs text-slate-600">{r.reasons.map((x) => <li key={x}>• {x}</li>)}</ul>
            </div>
          ))}
        </div>
      )}
      {tab === 'turnout' && turnout && !busy && (
        <div className="mt-4 space-y-2 text-sm">
          <p>
            Expected turnout: <b className="text-lg">{turnout.expected_turnout}</b> of {turnout.registered_approved} approved
            {' '}(range {turnout.range[0]}–{turnout.range[1]}; {turnout.expected_turnout_including_pending} if pending applicants are approved)
          </p>
          <p className="text-slate-600">Historical show-up rate: {turnout.historical_show_rate}% — {turnout.basis}.</p>
          <p className="text-xs text-slate-500">{turnout.disclaimer}</p>
        </div>
      )}
      {tab === 'summary' && (
        <div className="mt-4 space-y-2">
          <Field label="Organizer notes (used in the summary)">
            <textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          <button className="btn-primary btn-sm" onClick={genSummary} disabled={busy}>Generate summary from attendance data</button>
          {summary && <p className="whitespace-pre-line rounded-xl bg-slate-50 p-3 text-sm">{summary}</p>}
        </div>
      )}
    </section>
  )
}

function EmergencyForm({ event, onClose }) {
  const toast = useToast()
  const { register, handleSubmit, formState: { isSubmitting } } = useForm({
    defaultValues: { title: `Urgent: more volunteers for ${event.title}`, required_volunteers: 5, priority: 'HIGH', location: event.location },
  })
  const submit = async (v) => {
    try {
      const res = await eventService.emergencyCreate({ ...v, event: event.id, latitude: event.latitude, longitude: event.longitude, expires_at: new Date(v.expires_at).toISOString() })
      toast(`Emergency request sent to ${res.notified_count} people`)
      onClose()
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  const defaultExpiry = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 16)
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-3">
      <Field label="Title"><input className="input" {...register('title', { required: true })} /></Field>
      <Field label="Details"><textarea className="input" rows={3} {...register('description', { required: true })} /></Field>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Volunteers needed"><input type="number" min={1} className="input" {...register('required_volunteers', { required: true, valueAsNumber: true })} /></Field>
        <Field label="Priority">
          <select className="input" {...register('priority')}>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((p) => <option key={p}>{p}</option>)}</select>
        </Field>
        <Field label="Expires"><input type="datetime-local" className="input" defaultValue={defaultExpiry} {...register('expires_at', { required: true })} /></Field>
      </div>
      <Field label="Location"><input className="input" {...register('location', { required: true })} /></Field>
      <Field label="Skills needed" hint="Comma separated. Leave empty to alert all nearby volunteers."><input className="input" {...register('required_skills')} /></Field>
      <p className="text-xs text-slate-500">Notifies matching volunteers and nearby NSS coordinators in-app; HIGH/CRITICAL also send email.</p>
      <button className="btn-danger" disabled={isSubmitting}>🚨 Send emergency request</button>
    </form>
  )
}

export default function EventDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { user, isVolunteer, isAdmin, role } = useAuth()
  const { data: event, loading, error, reload } = useAsync(() => eventService.get(id), [id])
  const [busy, setBusy] = useState(false)
  const [groupOpen, setGroupOpen] = useState(false)
  const [emergencyOpen, setEmergencyOpen] = useState(false)
  const [groupCount, setGroupCount] = useState(10)
  const [groupMsg, setGroupMsg] = useState('')

  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />

  const act = async (fn, success) => {
    setBusy(true)
    try {
      await fn()
      if (success) toast(success)
      await reload()
    } catch (e) {
      toast(errorMessage(e), 'error')
    } finally {
      setBusy(false)
    }
  }
  const app = event.my_application
  const att = event.my_attendance
  const active = ['APPROVED', 'ONGOING'].includes(event.status)
  const ended = new Date(`${event.date}T${event.end_time}`) < new Date()
  const canRegister = isVolunteer && active && !ended && (!app || app.status === 'CANCELLED')
  const canCancel = isVolunteer && app && ['PENDING', 'APPROVED', 'WAITLISTED'].includes(app.status) && !att

  return (
    <div className="space-y-6">
      <Link to="/events" className="text-sm text-brand-700">← All drives</Link>
      <div className="card overflow-hidden">
        {event.event_image && <img src={event.event_image} alt={event.title ? `${event.title} – cover image` : 'Drive cover image'} className="h-56 w-full object-cover sm:h-72" />}
        <div className="p-5 sm:p-7">
          <div className="flex flex-wrap items-center gap-2">
            <CategoryBadge category={event.category} />
            <span className="badge bg-slate-50 text-slate-600 ring-slate-200">{event.theme_display}</span>
            <StatusBadge status={event.status} />
          </div>
          <h1 className="mt-3 text-2xl font-bold sm:text-3xl">{event.title}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            by {event.ngo ? <Link to={`/ngos/${event.ngo}`} className="font-medium text-brand-700">{event.organizer_display}</Link> : event.nss_unit ? <Link to={`/nss-units/${event.nss_unit}`} className="font-medium text-brand-700">{event.organizer_display}</Link> : event.organizer_display}
            <VerifiedBadge verified={event.ngo_verified} label="Verified NGO" />
          </p>
          <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div><p className="text-xs uppercase text-slate-500">Date</p><p className="font-medium">{formatDate(event.date, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p></div>
            <div><p className="text-xs uppercase text-slate-500">Time</p><p className="font-medium">{formatTime(event.start_time)} – {formatTime(event.end_time)}</p></div>
            <div><p className="text-xs uppercase text-slate-500">Location</p><p className="font-medium">{event.location}</p>{event.meeting_point && <p className="text-xs text-slate-500">Meet: {event.meeting_point}</p>}</div>
            <div><p className="text-xs uppercase text-slate-500">Volunteers</p><p className="font-medium">{event.approved_count}/{event.maximum_volunteers} confirmed · {event.spots_left} left</p></div>
          </div>

          {/* ------- volunteer actions ------- */}
          <div className="mt-6 flex flex-wrap items-center gap-2">
            {!user && active && <Link to="/login" state={{ from: `/events/${event.id}` }} className="btn-primary">Log in to register</Link>}
            {canRegister && (
              <button className="btn-primary" disabled={busy} onClick={() => act(() => applicationService.register(event.id), 'Application submitted')}>
                {event.spots_left === 0 ? 'Join waitlist' : 'Register for this drive'}
              </button>
            )}
            {app && app.status !== 'CANCELLED' && <span className="text-sm">Your registration: <StatusBadge status={app.status} /></span>}
            {canCancel && (
              <button className="btn-secondary" disabled={busy} onClick={() => window.confirm('Cancel your registration? The organizer will be notified.') && act(() => applicationService.cancel(event.id), 'Registration cancelled')}>
                Cancel registration
              </button>
            )}
            {isVolunteer && app?.status === 'APPROVED' && active && !att?.check_out && <Link to="/scan" className="btn-success">📷 Scan QR to {att ? 'check out' : 'check in'}</Link>}
            {role === 'NSS_COORDINATOR' && active && !ended && <button className="btn-secondary" onClick={() => setGroupOpen(true)}>Apply with my NSS unit</button>}
          </div>

          {att && (
            <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm">
              <p>
                Attendance: <StatusBadge status={att.status} />
                {att.check_in && <> · in {formatDateTime(att.check_in)}</>}
                {att.check_out && <> · out {formatDateTime(att.check_out)}</>}
                {att.hours != null && <> · <b>{att.hours}h</b> {att.hours_verified ? '(verified ✓)' : '(awaiting feedback)'}</>}
              </p>
              {att.certificate_id && (
                <p className="mt-1">📜 Certificate <Link className="font-semibold text-brand-700" to={`/certificate/${att.certificate_id}/verify`}>{att.certificate_id}</Link> · <Link to="/certificates" className="text-brand-700">download</Link></p>
              )}
              {att.check_out && !att.feedback_submitted && <div className="mt-3"><FeedbackForm event={event} onDone={reload} /></div>}
            </div>
          )}

          {/* ------- admin review ------- */}
          {isAdmin && event.can_manage && ['PENDING', 'REJECTED'].includes(event.status) && (
            <div className="mt-6 flex flex-wrap gap-2 rounded-xl bg-amber-50 p-4">
              <span className="w-full text-sm font-medium text-amber-800">Admin review</span>
              <button className="btn-success btn-sm" disabled={busy} onClick={() => act(() => eventService.approve(event.id), 'Drive approved')}>Approve</button>
              {event.status === 'PENDING' && (
                <button className="btn-danger btn-sm" disabled={busy} onClick={() => { const note = window.prompt('Reason for rejection (sent to organizer):'); if (note !== null) act(() => eventService.reject(event.id, note), 'Drive rejected') }}>Reject</button>
              )}
            </div>
          )}
          {event.can_manage && event.review_note && <p className="mt-3 text-sm text-slate-600">Review note: {event.review_note}</p>}
        </div>
      </div>

      {/* ------- organizer tools ------- */}
      {event.can_manage && (
        <section className="card p-5">
          <h2 className="mb-3 font-semibold">Organizer tools</h2>
          <div className="flex flex-wrap gap-2">
            <Link to={`/events/${event.id}/edit`} className="btn-secondary btn-sm">✏️ Edit</Link>
            <Link to={`/events/${event.id}/applications`} className="btn-secondary btn-sm">📝 Applications ({event.pending_count} pending)</Link>
            <Link to={`/events/${event.id}/attendance`} className="btn-secondary btn-sm">📷 QR & attendance</Link>
            {active && <button className="btn-secondary btn-sm" onClick={() => setEmergencyOpen(true)}>🚨 Emergency request</button>}
            {event.status === 'APPROVED' && <button className="btn-secondary btn-sm" disabled={busy} onClick={() => act(() => eventService.setStatus(event.id, 'ONGOING'), 'Marked ongoing')}>▶ Mark ongoing</button>}
            {active && <button className="btn-success btn-sm" disabled={busy} onClick={() => window.confirm('Complete this drive? Attendees still checked in are checked out at the scheduled end, absentees are marked, QR codes are deactivated.') && act(() => eventService.setStatus(event.id, 'COMPLETED'), 'Drive completed')}>✔ Complete drive</button>}
            {['PENDING', 'APPROVED', 'ONGOING'].includes(event.status) && <button className="btn-ghost btn-sm text-red-600" disabled={busy} onClick={() => window.confirm('Cancel this drive? Registered volunteers will be notified.') && act(() => eventService.setStatus(event.id, 'CANCELLED'), 'Drive cancelled')}>Cancel drive</button>}
            {['PENDING', 'REJECTED', 'CANCELLED'].includes(event.status) && <button className="btn-ghost btn-sm text-red-600" disabled={busy} onClick={() => window.confirm('Delete permanently?') && act(async () => { await eventService.remove(event.id); navigate('/events?mine=true') }, 'Deleted')}>Delete</button>}
          </div>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="card p-5">
            <h2 className="mb-2 font-semibold">About this drive</h2>
            <p className="whitespace-pre-line text-sm text-slate-700">{event.description}</p>
            {event.requirements && (<><h3 className="mb-1 mt-4 text-sm font-semibold">Requirements</h3><p className="whitespace-pre-line text-sm text-slate-700">{event.requirements}</p></>)}
            {event.instructions && (<><h3 className="mb-1 mt-4 text-sm font-semibold">Instructions</h3><p className="whitespace-pre-line text-sm text-slate-700">{event.instructions}</p></>)}
            {event.required_skills?.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">{event.required_skills.map((s) => <span key={s} className="rounded-lg bg-slate-100 px-2 py-0.5 text-xs">{s}</span>)}</div>
            )}
            {event.summary && (<><h3 className="mb-1 mt-4 text-sm font-semibold">Post-event summary</h3><p className="text-sm text-slate-700">{event.summary}</p></>)}
          </section>
          {event.can_manage && <AIPanel event={event} />}
          {['APPROVED', 'ONGOING', 'COMPLETED'].includes(event.status) && <Gallery event={event} />}
        </div>
        <div className="space-y-6">
          {event.latitude && <MapView height={260} markers={[{ id: event.id, lat: event.latitude, lng: event.longitude, type: 'event', title: event.title, subtitle: event.location }]} />}
          <section className="card p-5 text-sm">
            <h2 className="mb-2 font-semibold">Contact</h2>
            <p>✉️ <a className="text-brand-700" href={`mailto:${event.contact_email}`}>{event.contact_email}</a></p>
            {event.contact_phone && <p>📞 <a className="text-brand-700" href={`tel:${event.contact_phone}`}>{event.contact_phone}</a></p>}
            {event.latitude && <p className="mt-2"><a className="text-brand-700" target="_blank" rel="noreferrer" href={`https://www.openstreetmap.org/?mlat=${event.latitude}&mlon=${event.longitude}#map=16/${event.latitude}/${event.longitude}`}>Open in OpenStreetMap ↗</a></p>}
          </section>
        </div>
      </div>

      <Modal open={groupOpen} title="Apply as an NSS unit" onClose={() => setGroupOpen(false)}>
        <div className="space-y-3">
          <Field label="How many volunteers can your unit bring?"><input type="number" min={1} className="input" value={groupCount} onChange={(e) => setGroupCount(Number(e.target.value))} /></Field>
          <Field label="Message to the organizer"><textarea className="input" rows={3} value={groupMsg} onChange={(e) => setGroupMsg(e.target.value)} /></Field>
          <button className="btn-primary" disabled={busy} onClick={() => act(() => eventService.groupApply(event.id, { requested_volunteer_count: groupCount, message: groupMsg }), 'Group application sent').then(() => setGroupOpen(false))}>Send group application</button>
        </div>
      </Modal>
      <Modal open={emergencyOpen} title="Emergency volunteer request" onClose={() => setEmergencyOpen(false)}>
        <EmergencyForm event={event} onClose={() => setEmergencyOpen(false)} />
      </Modal>
    </div>
  )
}
