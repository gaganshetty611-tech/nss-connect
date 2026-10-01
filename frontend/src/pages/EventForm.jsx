import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage, fieldErrors } from '../services/api'
import eventService from '../services/eventService'
import { CATEGORIES, THEMES } from '../utils/constants'
import { toISODate } from '../utils/format'
import MapView from '../components/MapView'
import { ErrorAlert, Field, InfoAlert, PageHeader, Spinner } from '../components/ui'

export default function EventForm() {
  const { id } = useParams()
  const editing = Boolean(id)
  const navigate = useNavigate()
  const toast = useToast()
  const { user, canHost } = useAuth()
  const [loading, setLoading] = useState(editing)
  const [error, setError] = useState(null)
  const [suggestion, setSuggestion] = useState(null)
  const [timeHint, setTimeHint] = useState(null)
  const { register, handleSubmit, setValue, watch, reset, setError: setFieldError, formState: { errors, isSubmitting } } = useForm({
    defaultValues: { category: '', maximum_volunteers: 20, contact_email: user?.email, contact_phone: user?.phone || '' },
  })
  const [lat, lng, category, title, description] = watch(['latitude', 'longitude', 'category', 'title', 'description'])

  useEffect(() => {
    if (!editing) return
    eventService
      .get(id)
      .then((e) => {
        reset({ ...e, required_skills: (e.required_skills || []).join(', '), event_image: undefined, start_time: e.start_time?.slice(0, 5), end_time: e.end_time?.slice(0, 5) })
        setLoading(false)
      })
      .catch((e) => {
        setError(errorMessage(e))
        setLoading(false)
      })
  }, [editing, id, reset])

  useEffect(() => {
    if (!category) return setTimeHint(null)
    eventService.suggestDatetime(category).then(setTimeHint).catch(() => setTimeHint(null))
  }, [category])

  const suggest = async () => {
    try {
      const s = await eventService.categorize(title || '', description || '')
      setSuggestion(s)
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }

  const useMyLocation = () =>
    navigator.geolocation?.getCurrentPosition(
      (p) => {
        setValue('latitude', p.coords.latitude.toFixed(6))
        setValue('longitude', p.coords.longitude.toFixed(6))
      },
      () => toast('Location permission denied', 'error'),
    )

  const onSubmit = async (values) => {
    setError(null)
    const file = values.event_image?.[0]
    const FIELDS = ['title', 'description', 'category', 'theme', 'date', 'start_time', 'end_time', 'location', 'latitude', 'longitude',
      'maximum_volunteers', 'requirements', 'meeting_point', 'contact_email', 'contact_phone', 'instructions']
    const data = {
      ...Object.fromEntries(FIELDS.map((k) => [k, values[k] ?? ''])),
      event_image: file || undefined,
      required_skills: (values.required_skills || '').split(',').map((s) => s.trim()).filter(Boolean),
      latitude: values.latitude === '' ? null : values.latitude,
      longitude: values.longitude === '' ? null : values.longitude,
      theme: values.theme || undefined,
    }
    if (file) {
      if (data.latitude === null) delete data.latitude
      if (data.longitude === null) delete data.longitude
    }
    try {
      const saved = editing ? await eventService.update(id, data) : await eventService.create(data)
      toast(saved.status === 'APPROVED' ? 'Drive saved and published' : 'Drive submitted for admin approval')
      navigate(`/events/${saved.id}`)
    } catch (e) {
      Object.entries(fieldErrors(e)).forEach(([k, v]) => setFieldError(k, { message: v }))
      setError(errorMessage(e))
    }
  }

  if (!canHost) {
    return (
      <div className="card mx-auto max-w-xl p-8 text-center">
        <h1 className="text-xl font-bold">Host a drive</h1>
        <p className="mt-2 text-sm text-slate-600">Drives are hosted by verified NGOs, NSS coordinators and administrators.</p>
        <div className="mt-4 flex justify-center gap-2">
          {!user && <Link to="/login" className="btn-primary">Log in</Link>}
          {!user && <Link to="/register" className="btn-secondary">Register as NGO / NSS coordinator</Link>}
        </div>
      </div>
    )
  }
  if (loading) return <Spinner />

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title={editing ? 'Edit drive' : 'Host a drive'} subtitle={editing ? 'Changing title, date, time, location or category of an approved drive sends it back for re-approval.' : 'New drives are reviewed by an administrator before volunteers can see them.'} />
      {user.organization && user.organization.status !== 'VERIFIED' && !['SUPER_ADMIN', 'UNIVERSITY_ADMIN', 'COLLEGE_ADMIN'].includes(user.role) && (
        <div className="mb-4"><InfoAlert tone="warn">{user.organization.name} is not verified yet, so the server will not accept new drives.</InfoAlert></div>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <ErrorAlert message={error} />
        <section className="card space-y-4 p-5">
          <Field label="Title" error={errors.title?.message}><input className="input" {...register('title', { required: 'Required', maxLength: 200 })} /></Field>
          <Field label="Description" error={errors.description?.message}><textarea rows={4} className="input" {...register('description', { required: 'Required' })} /></Field>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="btn-secondary btn-sm" onClick={suggest} disabled={!title && !description}>✨ Suggest category from description</button>
            {suggestion && (
              <span className="text-xs text-slate-600">
                {suggestion.category ? (
                  <>
                    Suggested <b>{CATEGORIES.find((c) => c.value === suggestion.category)?.label}</b> / {THEMES.find((t) => t.value === suggestion.theme)?.label} ({Math.round(suggestion.confidence * 100)}% keyword share){' '}
                    <button type="button" className="font-semibold text-brand-700" onClick={() => { setValue('category', suggestion.category); setValue('theme', suggestion.theme) }}>Apply</button>
                  </>
                ) : suggestion.reasons[0]}
              </span>
            )}
          </div>
          {suggestion?.category && <ul className="text-xs text-slate-500">{suggestion.reasons.map((r) => <li key={r}>• {r}</li>)}</ul>}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Category" error={errors.category?.message}>
              <select className="input" {...register('category', { required: 'Choose a category' })}>
                <option value="">Select…</option>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label} — {c.hint}</option>)}
              </select>
            </Field>
            <Field label="Theme" hint="Leave blank to auto-tag from the description.">
              <select className="input" {...register('theme')}>
                <option value="">Auto</option>
                {THEMES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
          </div>
        </section>

        <section className="card space-y-4 p-5">
          <h2 className="font-semibold">When</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Date" error={errors.date?.message}><input type="date" min={editing ? undefined : toISODate(new Date())} className="input" {...register('date', { required: 'Required' })} /></Field>
            <Field label="Start time" error={errors.start_time?.message}><input type="time" className="input" {...register('start_time', { required: 'Required' })} /></Field>
            <Field label="End time" error={errors.end_time?.message}><input type="time" className="input" {...register('end_time', { required: 'Required' })} /></Field>
          </div>
          {timeHint && (
            <p className="rounded-xl bg-brand-50 px-3 py-2 text-xs text-brand-800">
              ⏰ Best turnout historically: {timeHint.suggestions.map((s) => `${s.weekday} ${s.slot_label}${s.turnout_rate != null ? ` (${s.turnout_rate}%)` : ''}`).join(' · ')}. <span className="text-brand-600">{timeHint.basis}</span>
            </p>
          )}
        </section>

        <section className="card space-y-4 p-5">
          <h2 className="font-semibold">Where</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Location" error={errors.location?.message}><input className="input" {...register('location', { required: 'Required' })} /></Field>
            <Field label="Meeting point"><input className="input" {...register('meeting_point')} /></Field>
            <Field label="Latitude" error={errors.latitude?.message}><input className="input" inputMode="decimal" {...register('latitude')} /></Field>
            <Field label="Longitude" error={errors.longitude?.message}><input className="input" inputMode="decimal" {...register('longitude')} /></Field>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Click the map to set coordinates (OpenStreetMap).</span>
            <button type="button" className="text-brand-700" onClick={useMyLocation}>Use my current location</button>
          </div>
          <MapView height={280} picked={{ lat: lat || null, lng: lng || null }} onPick={(la, ln) => { setValue('latitude', String(la)); setValue('longitude', String(ln)) }} />
        </section>

        <section className="card space-y-4 p-5">
          <h2 className="font-semibold">Volunteers & details</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Maximum volunteers" error={errors.maximum_volunteers?.message}><input type="number" min={1} className="input" {...register('maximum_volunteers', { required: 'Required', valueAsNumber: true, min: { value: 1, message: 'At least 1' } })} /></Field>
            <Field label="Required skills" hint="Comma separated"><input className="input" {...register('required_skills')} /></Field>
            <Field label="Contact email" error={errors.contact_email?.message}><input type="email" className="input" {...register('contact_email', { required: 'Required' })} /></Field>
            <Field label="Contact phone" error={errors.contact_phone?.message}><input type="tel" className="input" {...register('contact_phone')} /></Field>
          </div>
          <Field label="Requirements"><textarea rows={2} className="input" {...register('requirements')} /></Field>
          <Field label="Instructions"><textarea rows={2} className="input" {...register('instructions')} /></Field>
          <Field label="Event image" hint="JPG, PNG or WebP, up to 5 MB" error={errors.event_image?.message}><input type="file" accept="image/jpeg,image/png,image/webp" className="text-sm" {...register('event_image')} /></Field>
        </section>

        <div className="flex gap-2">
          <button className="btn-primary" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Submit drive'}</button>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
