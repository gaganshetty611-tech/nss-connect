import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import authService from '../services/authService'
import nssService from '../services/nssService'
import { INTERESTS, ROLES, WEEKDAYS } from '../utils/constants'
import { pretty } from '../utils/format'
import { ErrorAlert, Field, PageHeader } from '../components/ui'

export default function Profile() {
  const { user, setUser, isVolunteer } = useAuth()
  const toast = useToast()
  const [colleges, setColleges] = useState([])
  const [units, setUnits] = useState([])
  const [error, setError] = useState(null)
  const vp = user.volunteer_profile
  const { register, handleSubmit, watch, formState: { isSubmitting } } = useForm({
    defaultValues: {
      first_name: user.first_name, last_name: user.last_name, phone: user.phone, gender: user.gender,
      bio: user.profile?.bio, city: user.profile?.city, latitude: user.profile?.latitude || '', longitude: user.profile?.longitude || '',
      college: user.profile?.college || '', nss_unit: vp?.nss_unit || '', roll_number: vp?.roll_number || '', year_of_study: vp?.year_of_study || '',
      skills: vp?.skills.join(', ') || '', interests: vp?.interests || [], availability: vp?.availability || [],
    },
  })
  const college = watch('college')
  useEffect(() => { nssService.colleges().then(setColleges).catch(() => {}) }, [])
  useEffect(() => {
    if (college) nssService.list({ college, page_size: 100 }).then((d) => setUnits(d.results)).catch(() => {})
  }, [college])

  const save = async (v) => {
    setError(null)
    const payload = {
      first_name: v.first_name, last_name: v.last_name, phone: v.phone, gender: v.gender, bio: v.bio || '', city: v.city || '',
      latitude: v.latitude || null, longitude: v.longitude || null,
    }
    if (!['COLLEGE_ADMIN', 'UNIVERSITY_ADMIN', 'SUPER_ADMIN'].includes(user.role)) payload.college = v.college || null
    if (isVolunteer) Object.assign(payload, {
      nss_unit: v.nss_unit || null, roll_number: v.roll_number || '', year_of_study: v.year_of_study || null,
      skills: v.skills, interests: v.interests || [], availability: v.availability || [],
    })
    try {
      setUser(await authService.updateProfile(payload))
      toast('Profile saved')
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const upload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    try {
      setUser(await authService.uploadPhoto(file))
      toast('Photo updated')
    } catch (err) {
      toast(errorMessage(err), 'error')
    }
  }
  const [pw, setPw] = useState({ current: '', next: '' })
  const changePw = async (e) => {
    e.preventDefault()
    try {
      await authService.changePassword(pw.current, pw.next)
      setPw({ current: '', next: '' })
      toast('Password changed')
    } catch (err) {
      toast(errorMessage(err), 'error')
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title="Profile" subtitle={`${ROLES[user.role]} · ${user.email}${user.is_email_verified ? ' · email verified ✓' : ''}`} />
      <section className="card flex items-center gap-4 p-5">
        {user.photo_url ? <img src={user.photo_url} alt="Your profile photo" className="h-20 w-20 rounded-full object-cover" /> : <div className="grid h-20 w-20 place-items-center rounded-full bg-brand-100 text-2xl">👤</div>}
        <div>
          <label className="btn-secondary btn-sm cursor-pointer">Upload photo<input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={upload} /></label>
          <p className="mt-1 text-xs text-slate-500">JPG, PNG or WebP · max 5 MB</p>
        </div>
      </section>
      <form onSubmit={handleSubmit(save)} className="card space-y-4 p-5">
        <ErrorAlert message={error} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="First name"><input className="input" {...register('first_name')} /></Field>
          <Field label="Last name"><input className="input" {...register('last_name')} /></Field>
          <Field label="Phone"><input className="input" {...register('phone')} /></Field>
          <Field label="Gender">
            <select className="input" {...register('gender')}>
              <option value="UNDISCLOSED">Prefer not to say</option><option value="FEMALE">Female</option><option value="MALE">Male</option><option value="OTHER">Other</option>
            </select>
          </Field>
          <Field label="City"><input className="input" {...register('city')} /></Field>
          {!['COLLEGE_ADMIN', 'UNIVERSITY_ADMIN', 'SUPER_ADMIN'].includes(user.role) && (
            <Field label="College">
              <select className="input" {...register('college')}><option value="">—</option>{colleges.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
            </Field>
          )}
        </div>
        <Field label="Bio"><textarea rows={3} className="input" {...register('bio')} /></Field>
        {isVolunteer && (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="NSS unit">
                <select className="input" {...register('nss_unit')}><option value="">—</option>{units.map((u) => <option key={u.id} value={u.id}>{u.display_name}</option>)}</select>
              </Field>
              <Field label="Roll number"><input className="input" {...register('roll_number')} /></Field>
              <Field label="Year of study"><input type="number" min={1} max={10} className="input" {...register('year_of_study')} /></Field>
            </div>
            <Field label="Skills" hint="Comma separated"><input className="input" {...register('skills')} /></Field>
            <Field label="Interests">
              <div className="flex flex-wrap gap-2">{INTERESTS.map((i) => <label key={i} className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2 py-1 text-xs ring-1 ring-slate-200"><input type="checkbox" value={i} {...register('interests')} /> {pretty(i)}</label>)}</div>
            </Field>
            <Field label="Availability">
              <div className="flex flex-wrap gap-2">{WEEKDAYS.map((d) => <label key={d} className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2 py-1 text-xs ring-1 ring-slate-200"><input type="checkbox" value={d} {...register('availability')} /> {d}</label>)}</div>
            </Field>
          </>
        )}
        <button className="btn-primary" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : 'Save profile'}</button>
      </form>
      <form onSubmit={changePw} className="card space-y-3 p-5">
        <h2 className="font-semibold">Change password</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input className="input" type="password" placeholder="Current password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
          <input className="input" type="password" placeholder="New password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
        </div>
        <button className="btn-secondary" disabled={!pw.current || pw.next.length < 8}>Change password</button>
      </form>
    </div>
  )
}
