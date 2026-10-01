import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage, fieldErrors } from '../services/api'
import eventService from '../services/eventService'
import ngoService from '../services/ngoService'
import useAsync from '../utils/useAsync'
import { FOCUS_AREAS } from '../utils/constants'
import { formatDate, pretty } from '../utils/format'
import EventCard from '../components/EventCard'
import MapView from '../components/MapView'
import { EmptyState, ErrorAlert, Field, InfoAlert, PageHeader, Pagination, Spinner, StatusBadge, VerifiedBadge } from '../components/ui'

export function NgoList() {
  const { role } = useAuth()
  const [search, setSearch] = useState('')
  const [focus, setFocus] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => ngoService.list({ search: search || undefined, focus_area: focus || undefined, page }), [search, focus, page])
  return (
    <div>
      <PageHeader
        title="NGO Hub"
        subtitle="Only NGOs verified by administrators carry the Verified badge and can post drives."
        actions={role === 'NGO_ORGANIZER' && <Link to="/ngos/new" className="btn-primary">Register your NGO</Link>}
      />
      <div className="card mb-6 grid gap-3 p-4 sm:grid-cols-3">
        <input className="input sm:col-span-2" placeholder="Search NGOs…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
        <select className="input" value={focus} onChange={(e) => { setFocus(e.target.value); setPage(1) }}>
          <option value="">All focus areas</option>
          {FOCUS_AREAS.map((f) => <option key={f} value={f}>{pretty(f)}</option>)}
        </select>
      </div>
      {loading && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data?.results.length === 0 && <EmptyState title="No NGOs found" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((n) => (
          <Link key={n.id} to={`/ngos/${n.id}`} className="card flex gap-4 p-5 transition hover:shadow-lg">
            {n.logo ? <img src={n.logo} alt={`${n.name} logo`} className="h-14 w-14 shrink-0 rounded-xl object-cover" /> : <div className="grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-green-50 text-2xl">🏢</div>}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <h3 className="font-semibold">{n.name}</h3>
                {n.verified ? <VerifiedBadge verified /> : <StatusBadge status={n.verification_status} />}
              </div>
              <p className="text-xs text-slate-500">📍 {n.location || '—'}</p>
              <p className="mt-1 line-clamp-2 text-sm text-slate-600">{n.description}</p>
              <p className="mt-2 text-xs text-slate-500">{n.upcoming_event_count} upcoming · {n.event_count} total drives</p>
              <div className="mt-2 flex flex-wrap gap-1">{n.focus_areas.map((f) => <span key={f} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px]">{pretty(f)}</span>)}</div>
            </div>
          </Link>
        ))}
      </div>
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

function Documents({ ngo, isOwner, canReview }) {
  const toast = useToast()
  const { data, reload } = useAsync(() => ngoService.documents(ngo.id), [ngo.id])
  const [type, setType] = useState('REGISTRATION_CERTIFICATE')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const upload = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await ngoService.uploadDocument(ngo.id, type, file)
      toast('Document uploaded for review')
      setFile(null)
      e.target.reset()
      reload()
    } catch (err) {
      toast(errorMessage(err), 'error')
    } finally {
      setBusy(false)
    }
  }
  const review = async (doc, status) => {
    try {
      await ngoService.reviewDocument(doc.id, status, '')
      reload()
    } catch (err) {
      toast(errorMessage(err), 'error')
    }
  }
  return (
    <section className="card p-5">
      <h2 className="mb-1 font-semibold">Verification documents</h2>
      <p className="mb-3 text-xs text-slate-500">Private: visible only to the NGO owner and administrators. PDF/JPG/PNG, max 10 MB.</p>
      {data?.length ? (
        <ul className="divide-y divide-slate-100 text-sm">
          {data.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                <button className="font-medium text-brand-700" onClick={() => ngoService.downloadDocument(d)}>{d.document_type_display}</button>
                <span className="ml-2 text-xs text-slate-500">{d.original_filename} · {formatDate(d.uploaded_at)}</span>
              </span>
              <span className="flex items-center gap-2">
                <StatusBadge status={d.status} />
                {canReview && d.status === 'PENDING' && (
                  <>
                    <button className="btn-success btn-sm" onClick={() => review(d, 'APPROVED')}>Approve</button>
                    <button className="btn-ghost btn-sm text-red-600" onClick={() => review(d, 'REJECTED')}>Reject</button>
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">No documents uploaded.</p>
      )}
      {isOwner && (
        <form onSubmit={upload} className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
          <select className="input sm:w-56" value={type} onChange={(e) => setType(e.target.value)}>
            {[['REGISTRATION_CERTIFICATE', 'Registration Certificate'], ['PAN', 'PAN Card'], ['12A', '12A Certificate'], ['80G', '80G Certificate'], ['FCRA', 'FCRA Registration'], ['OTHER', 'Other']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input type="file" accept="application/pdf,image/jpeg,image/png" className="text-sm" onChange={(e) => setFile(e.target.files[0])} />
          <button className="btn-secondary" disabled={!file || busy}>{busy ? 'Uploading…' : 'Upload'}</button>
        </form>
      )}
    </section>
  )
}

export function NgoDetail() {
  const { id } = useParams()
  const toast = useToast()
  const { user, permissions } = useAuth()
  const { data: ngo, loading, error, reload } = useAsync(() => ngoService.get(id), [id])
  const events = useAsync(() => eventService.list({ ngo: id, page_size: 6 }), [id])
  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const isOwner = user && ngo.owner === user.id
  const setStatus = async (fn, label) => {
    const note = label === 'verified' ? '' : window.prompt(`Note for the NGO (why ${label}?)`)
    if (note === null) return
    try {
      await fn(ngo.id, note)
      toast(`NGO ${label}`)
      reload()
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  return (
    <div className="space-y-6">
      <Link to="/ngos" className="text-sm text-brand-700">← NGO Hub</Link>
      <div className="card flex flex-col gap-5 p-6 sm:flex-row">
        {ngo.logo ? <img src={ngo.logo} alt={`${ngo.name} logo`} className="h-24 w-24 rounded-2xl object-cover" /> : <div className="grid h-24 w-24 place-items-center rounded-2xl bg-green-50 text-4xl">🏢</div>}
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold">{ngo.name}</h1>
            {ngo.verified ? <VerifiedBadge verified /> : <StatusBadge status={ngo.verification_status} />}
          </div>
          <p className="mt-1 text-sm text-slate-500">📍 {ngo.location}</p>
          <p className="mt-3 whitespace-pre-line text-sm text-slate-700">{ngo.description}</p>
          <div className="mt-3 flex flex-wrap gap-3 text-sm">
            <a className="text-brand-700" href={`mailto:${ngo.email}`}>{ngo.email}</a>
            {ngo.phone && <a className="text-brand-700" href={`tel:${ngo.phone}`}>{ngo.phone}</a>}
            {ngo.website && <a className="text-brand-700" href={ngo.website} target="_blank" rel="noreferrer noopener">{ngo.website} ↗</a>}
          </div>
          {ngo.review_note && <p className="mt-2 text-sm text-amber-700">Review note: {ngo.review_note}</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            {isOwner && <Link to={`/ngos/${ngo.id}/edit`} className="btn-secondary btn-sm">Edit NGO</Link>}
            {permissions.reviewNgos && ngo.verification_status !== 'VERIFIED' && <button className="btn-success btn-sm" onClick={() => setStatus(ngoService.verify, 'verified')}>Verify NGO</button>}
            {permissions.reviewNgos && ngo.verification_status === 'PENDING' && <button className="btn-danger btn-sm" onClick={() => setStatus(ngoService.reject, 'rejected')}>Reject</button>}
            {permissions.reviewNgos && ngo.verification_status === 'VERIFIED' && <button className="btn-danger btn-sm" onClick={() => setStatus(ngoService.suspend, 'suspended')}>Suspend</button>}
          </div>
        </div>
      </div>
      {isOwner && ngo.verification_status === 'PENDING' && <InfoAlert tone="warn">Upload your registration documents below. An administrator will verify your NGO before you can post drives.</InfoAlert>}
      {(isOwner || permissions.manageUsers) && <Documents ngo={ngo} isOwner={isOwner} canReview={permissions.reviewNgos} />}
      {ngo.latitude && <MapView height={260} markers={[{ id: ngo.id, lat: ngo.latitude, lng: ngo.longitude, type: 'ngo', title: ngo.name, subtitle: ngo.location }]} />}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Upcoming drives</h2>
        {events.data?.results.length ? (
          <div className="card overflow-hidden">{events.data.results.map((e) => <EventCard key={e.id} event={e} />)}</div>
        ) : (
          <p className="text-sm text-slate-500">No upcoming drives.</p>
        )}
      </section>
    </div>
  )
}

export function NgoForm() {
  const { id } = useParams()
  const editing = Boolean(id)
  const navigate = useNavigate()
  const toast = useToast()
  const { refreshUser } = useAuth()
  const [error, setError] = useState(null)
  const { register, handleSubmit, reset, setValue, watch, setError: setFieldError, formState: { errors, isSubmitting } } = useForm({ defaultValues: { focus_areas: [] } })
  const [lat, lng] = watch(['latitude', 'longitude'])
  useEffect(() => {
    if (editing) ngoService.get(id).then((n) => reset({ ...n, logo: undefined })).catch((e) => setError(errorMessage(e)))
  }, [editing, id, reset])
  const onSubmit = async (v) => {
    setError(null)
    const data = {
      name: v.name, description: v.description, location: v.location, email: v.email, phone: v.phone, website: v.website,
      registration_number: v.registration_number, focus_areas: v.focus_areas || [],
      latitude: v.latitude || null, longitude: v.longitude || null, logo: v.logo?.[0],
    }
    if (data.logo) {
      if (!data.latitude) delete data.latitude
      if (!data.longitude) delete data.longitude
    }
    try {
      const saved = editing ? await ngoService.update(id, data) : await ngoService.create(data)
      await refreshUser()
      toast(editing ? 'NGO updated' : 'NGO registered – upload documents for verification')
      navigate(`/ngos/${saved.id}`)
    } catch (e) {
      Object.entries(fieldErrors(e)).forEach(([k, m]) => setFieldError(k, { message: m }))
      setError(errorMessage(e))
    }
  }
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title={editing ? 'Edit NGO' : 'Register your NGO'} subtitle="Administrators verify NGOs before they can post drives." />
      <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4 p-5">
        <ErrorAlert message={error} />
        <Field label="NGO name" error={errors.name?.message}><input className="input" {...register('name', { required: 'Required' })} /></Field>
        <Field label="Description"><textarea rows={4} className="input" {...register('description')} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Email" error={errors.email?.message}><input type="email" className="input" {...register('email', { required: 'Required' })} /></Field>
          <Field label="Phone"><input className="input" {...register('phone')} /></Field>
          <Field label="Website" error={errors.website?.message}><input type="url" className="input" placeholder="https://" {...register('website')} /></Field>
          <Field label="Registration number"><input className="input" {...register('registration_number')} /></Field>
          <Field label="Location"><input className="input" {...register('location')} /></Field>
          <Field label="Logo" hint="JPG/PNG/WebP up to 5 MB" error={errors.logo?.message}><input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" {...register('logo')} /></Field>
          <Field label="Latitude"><input className="input" {...register('latitude')} /></Field>
          <Field label="Longitude"><input className="input" {...register('longitude')} /></Field>
        </div>
        <MapView height={240} picked={{ lat: lat || null, lng: lng || null }} onPick={(a, b) => { setValue('latitude', String(a)); setValue('longitude', String(b)) }} />
        <Field label="Focus areas" error={errors.focus_areas?.message}>
          <div className="flex flex-wrap gap-2">
            {FOCUS_AREAS.map((f) => (
              <label key={f} className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2 py-1 text-xs ring-1 ring-slate-200">
                <input type="checkbox" value={f} {...register('focus_areas')} /> {pretty(f)}
              </label>
            ))}
          </div>
        </Field>
        <button className="btn-primary" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : editing ? 'Save' : 'Register NGO'}</button>
      </form>
    </div>
  )
}
