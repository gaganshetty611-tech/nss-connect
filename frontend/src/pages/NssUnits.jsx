import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import eventService from '../services/eventService'
import nssService from '../services/nssService'
import useAsync from '../utils/useAsync'
import { CATEGORY_LABEL } from '../utils/constants'
import EventCard from '../components/EventCard'
import MapView from '../components/MapView'
import { EmptyState, ErrorAlert, Field, Modal, PageHeader, Spinner, StatCard, StatusBadge, VerifiedBadge } from '../components/ui'

function UnitForm({ onSaved }) {
  const toast = useToast()
  const [unis, setUnis] = useState([])
  const [colleges, setColleges] = useState([])
  const { register, handleSubmit, watch, setValue, formState: { isSubmitting } } = useForm()
  const [uni, lat, lng] = watch(['university', 'latitude', 'longitude'])
  useEffect(() => { nssService.universities().then(setUnis) }, [])
  useEffect(() => { nssService.colleges(uni ? { university: uni } : {}).then(setColleges) }, [uni])
  const submit = async (v) => {
    try {
      const unit = await nssService.create({ college: v.college, unit_number: v.unit_number, email: v.email, phone: v.phone, location: v.location, latitude: v.latitude || null, longitude: v.longitude || null })
      toast('NSS unit registered – awaiting verification')
      onSaved(unit)
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="University"><select className="input" {...register('university')}><option value="">All</option>{unis.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</select></Field>
        <Field label="College"><select className="input" {...register('college', { required: true })}><option value="">Select…</option>{colleges.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        <Field label="Unit number"><input className="input" {...register('unit_number', { required: true })} /></Field>
        <Field label="Unit email"><input type="email" className="input" {...register('email')} /></Field>
        <Field label="Phone"><input className="input" {...register('phone')} /></Field>
        <Field label="Location"><input className="input" {...register('location')} /></Field>
        <Field label="Latitude"><input className="input" {...register('latitude')} /></Field>
        <Field label="Longitude"><input className="input" {...register('longitude')} /></Field>
      </div>
      <MapView height={200} picked={{ lat: lat || null, lng: lng || null }} onPick={(a, b) => { setValue('latitude', String(a)); setValue('longitude', String(b)) }} />
      <button className="btn-primary" disabled={isSubmitting}>Register unit</button>
    </form>
  )
}

export function NssUnitList() {
  const { role } = useAuth()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const { data, loading, error, reload } = useAsync(() => nssService.list({ search: search || undefined, page_size: 50 }), [search])
  const open = params.get('new') === '1'
  return (
    <div>
      <PageHeader title="NSS Units" subtitle="Verified college NSS units. Coordinators apply to drives as a group; volunteers join under their unit." actions={['NSS_COORDINATOR', 'SUPER_ADMIN', 'UNIVERSITY_ADMIN', 'COLLEGE_ADMIN'].includes(role) && <button className="btn-primary" onClick={() => setParams({ new: '1' })}>Register NSS unit</button>} />
      <input className="input mb-4 max-w-md" placeholder="Search by college or unit…" value={search} onChange={(e) => setSearch(e.target.value)} />
      {loading && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data?.results.length === 0 && <EmptyState title="No NSS units yet" />}
      {data?.results.length > 0 && (
        <>
          <MapView height={300} markers={data.results.map((u) => ({ id: u.id, lat: u.latitude, lng: u.longitude, type: 'unit', title: u.display_name, subtitle: `${u.volunteer_count} volunteers`, link: `/nss-units/${u.id}` }))} />
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.results.map((u) => (
              <Link key={u.id} to={`/nss-units/${u.id}`} className="card p-5 hover:shadow-lg">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-semibold">{u.college_name}</h3>
                  {u.verified ? <VerifiedBadge verified /> : <StatusBadge status={u.verification_status} />}
                </div>
                <p className="text-sm text-slate-600">NSS Unit {u.unit_number} · {u.university_name}</p>
                <p className="mt-2 text-xs text-slate-500">👥 {u.volunteer_count} volunteers · Coordinator: {u.coordinator_name || '—'}</p>
              </Link>
            ))}
          </div>
        </>
      )}
      <Modal open={open} title="Register an NSS unit" onClose={() => setParams({})} wide>
        <UnitForm onSaved={() => { setParams({}); reload() }} />
      </Modal>
    </div>
  )
}

export function NssUnitDetail() {
  const { id } = useParams()
  const toast = useToast()
  const { user, isAdmin } = useAuth()
  const { data: unit, loading, error, reload } = useAsync(() => nssService.get(id), [id])
  const stats = useAsync(() => nssService.stats(id), [id])
  const events = useAsync(() => eventService.list({ nss_unit: id, page_size: 6 }), [id])
  const canSeeMembers = unit && user && (unit.coordinator === user.id || isAdmin)
  const members = useAsync(() => (canSeeMembers ? nssService.members(id) : Promise.resolve([])), [id, canSeeMembers])
  if (loading) return <Spinner />
  if (error) return <ErrorAlert message={error} onRetry={reload} />
  const setStatus = async (fn, label) => {
    try {
      await fn(unit.id, '')
      toast(`Unit ${label}`)
      reload()
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  const s = stats.data
  return (
    <div className="space-y-6">
      <Link to="/nss-units" className="text-sm text-brand-700">← NSS units</Link>
      <div className="card p-6">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold">{unit.display_name}</h1>
          {unit.verified ? <VerifiedBadge verified /> : <StatusBadge status={unit.verification_status} />}
        </div>
        <p className="mt-1 text-sm text-slate-600">{unit.university_name} · Coordinator: {unit.coordinator_name || '—'}</p>
        <p className="mt-1 text-sm text-slate-500">{unit.email} {unit.phone && `· ${unit.phone}`} {unit.location && `· 📍 ${unit.location}`}</p>
        {isAdmin && (
          <div className="mt-4 flex gap-2">
            {unit.verification_status !== 'VERIFIED' && <button className="btn-success btn-sm" onClick={() => setStatus(nssService.verify, 'verified')}>Verify unit</button>}
            {unit.verification_status === 'PENDING' && <button className="btn-danger btn-sm" onClick={() => setStatus(nssService.reject, 'rejected')}>Reject</button>}
            {unit.verification_status === 'VERIFIED' && <button className="btn-danger btn-sm" onClick={() => setStatus(nssService.suspend, 'suspended')}>Suspend</button>}
          </div>
        )}
      </div>
      {s && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Volunteers" value={s.volunteer_count} />
          <StatCard label="Attendances" value={s.events_attended} />
          <StatCard label="Attendance rate" value={s.attendance_rate == null ? '—' : `${s.attendance_rate}%`} />
          <StatCard label="Verified hours" value={s.verified_hours} hint={Object.entries(s.hours_by_category).map(([k, v]) => `${CATEGORY_LABEL[k]} ${v}h`).join(' · ')} />
        </div>
      )}
      {unit.latitude && <MapView height={240} markers={[{ id: unit.id, lat: unit.latitude, lng: unit.longitude, type: 'unit', title: unit.display_name }]} />}
      {canSeeMembers && (
        <section className="card overflow-x-auto">
          <h2 className="px-5 pt-5 font-semibold">Members ({members.data?.length || 0})</h2>
          <table className="table mt-3">
            <thead><tr><th>Name</th><th>Email</th><th>Skills</th><th>Availability</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {(members.data || []).map((m) => (
                <tr key={m.id}><td className="font-medium">{m.full_name}</td><td>{m.email}</td><td className="text-xs">{m.volunteer_profile?.skills.join(', ')}</td><td className="text-xs">{m.volunteer_profile?.availability.join(', ')}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Drives hosted by this unit</h2>
        {events.data?.results.length ? <div className="card overflow-hidden">{events.data.results.map((e) => <EventCard key={e.id} event={e} />)}</div> : <p className="text-sm text-slate-500">No upcoming drives.</p>}
      </section>
    </div>
  )
}
