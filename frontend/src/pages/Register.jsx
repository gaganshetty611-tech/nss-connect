import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage, fieldErrors } from '../services/api'
import authService from '../services/authService'
import nssService from '../services/nssService'
import { ErrorAlert, Field, InfoAlert } from '../components/ui'
import { INTERESTS, WEEKDAYS } from '../utils/constants'
import { pretty } from '../utils/format'
import { useSpamGuard } from '../utils/spam'
import { AuthShell, GoogleButton } from './Login'

export default function Register() {
  const [universities, setUniversities] = useState([])
  const [colleges, setColleges] = useState([])
  const [units, setUnits] = useState([])
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  const { register, handleSubmit, watch, setError: setFieldError, formState: { errors, isSubmitting } } = useForm({
    mode: 'onTouched',
    defaultValues: { role: 'VOLUNTEER', gender: 'UNDISCLOSED', interests: [], availability: [] },
  })
  const { honeypot, isBot } = useSpamGuard(register)
  const role = watch('role')
  const university = watch('university')
  const college = watch('college')

  useEffect(() => {
    nssService.universities().then(setUniversities).catch(() => {})
  }, [])
  useEffect(() => {
    nssService.colleges(university ? { university } : {}).then(setColleges).catch(() => {})
  }, [university])
  useEffect(() => {
    if (!college) return setUnits([])
    nssService.list({ college, page_size: 100 }).then((d) => setUnits(d.results)).catch(() => {})
  }, [college])

  const onSubmit = async (values) => {
    setError(null)
    if (isBot(values)) return setError('We could not submit the form. Please wait a moment and try again.')
    const { website, ...clean } = values
    const payload = {
      ...clean,
      university: values.university || null,
      college: values.college || null,
      nss_unit: role === 'VOLUNTEER' && values.nss_unit ? values.nss_unit : null,
      skills: values.skills || '',
    }
    try {
      const res = await authService.register(payload)
      navigate('/welcome', { state: { email: res.user.email, detail: res.detail } })
    } catch (e) {
      const fe = fieldErrors(e)
      Object.entries(fe).forEach(([k, v]) => setFieldError(k, { message: v }))
      setError(errorMessage(e))
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Volunteers, NSS coordinators and NGO organizers can sign up here.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <ErrorAlert message={error} />
        {honeypot}
        <div className="grid grid-cols-3 gap-2">
          {[['VOLUNTEER', 'Volunteer'], ['NSS_COORDINATOR', 'NSS Coordinator'], ['NGO_ORGANIZER', 'NGO Organizer']].map(([v, l]) => (
            <label key={v} className={`cursor-pointer rounded-xl px-2 py-2 text-center text-xs font-semibold ring-1 ${role === v ? 'bg-brand-50 text-brand-700 ring-brand-300' : 'ring-slate-200 text-slate-600'}`}>
              <input type="radio" value={v} className="sr-only" {...register('role')} />
              {l}
            </label>
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="First name" error={errors.first_name?.message}>
            <input className="input" {...register('first_name', { required: 'First name is required' })} />
          </Field>
          <Field label="Last name" error={errors.last_name?.message}>
            <input className="input" {...register('last_name')} />
          </Field>
        </div>
        <Field label="Email" error={errors.email?.message}>
          <input className="input" type="email" autoComplete="email" {...register('email', { required: 'Email is required', pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email address' } })} />
        </Field>
        <Field label="Password" error={errors.password?.message} hint="At least 8 characters; not too common or all numbers.">
          <input className="input" type="password" autoComplete="new-password" {...register('password', { required: 'Password is required', minLength: { value: 8, message: 'At least 8 characters' }, validate: (v) => !/^\d+$/.test(v) || 'Password cannot be only numbers' })} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Phone" error={errors.phone?.message}>
            <input className="input" type="tel" autoComplete="tel" {...register('phone', { pattern: { value: /^[+()\-\s\d]{7,20}$/, message: 'Enter a valid phone number' } })} />
          </Field>
          <Field label="Gender" hint="Used only for aggregate NSS participation reports.">
            <select className="input" {...register('gender')}>
              <option value="UNDISCLOSED">Prefer not to say</option>
              <option value="FEMALE">Female</option>
              <option value="MALE">Male</option>
              <option value="OTHER">Other</option>
            </select>
          </Field>
        </div>
        {role !== 'NGO_ORGANIZER' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="University">
              <select className="input" {...register('university')}>
                <option value="">Select…</option>
                {universities.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </Field>
            <Field label="College" error={errors.college?.message}>
              <select className="input" {...register('college')}>
                <option value="">Select…</option>
                {colleges.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </Field>
          </div>
        )}
        {role === 'VOLUNTEER' && (
          <>
            <Field label="NSS unit" error={errors.nss_unit?.message} hint={college && !units.length ? 'No verified NSS unit for this college yet – you can join one later.' : undefined}>
              <select className="input" {...register('nss_unit')} disabled={!units.length}>
                <option value="">{units.length ? 'Select your unit…' : '—'}</option>
                {units.map((u) => <option key={u.id} value={u.id}>{u.display_name}</option>)}
              </select>
            </Field>
            <Field label="Skills" hint="Comma separated, e.g. Teaching, First Aid, Photography">
              <input className="input" {...register('skills')} />
            </Field>
            <Field label="Interests">
              <div className="flex flex-wrap gap-2">
                {INTERESTS.map((i) => (
                  <label key={i} className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2 py-1 text-xs ring-1 ring-slate-200">
                    <input type="checkbox" value={i} {...register('interests')} /> {pretty(i).replace('Abp1', 'ABP 1').replace('Abp2', 'ABP 2')}
                  </label>
                ))}
              </div>
            </Field>
            <Field label="Usually available on">
              <div className="flex flex-wrap gap-2">
                {WEEKDAYS.map((d) => (
                  <label key={d} className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-2 py-1 text-xs ring-1 ring-slate-200">
                    <input type="checkbox" value={d} {...register('availability')} /> {d}
                  </label>
                ))}
              </div>
            </Field>
          </>
        )}
        {role === 'NGO_ORGANIZER' && (
          <InfoAlert>After signing up you'll register your NGO and upload verification documents. Drives can be posted once an administrator verifies the NGO.</InfoAlert>
        )}
        {role === 'NSS_COORDINATOR' && (
          <InfoAlert>After signing up, register your NSS unit from the NSS Units page. A college or university admin verifies it.</InfoAlert>
        )}
        <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : 'Create account'}</button>
        <GoogleButton />
        <p className="text-center text-xs text-slate-500">
          By creating an account you agree to our <Link to="/terms" className="underline">Terms</Link> and <Link to="/privacy" className="underline">Privacy Policy</Link>.
        </p>
        <p className="text-center text-sm text-slate-500">
          Already registered? <Link to="/login" className="font-semibold text-brand-700">Log in</Link>
        </p>
      </form>
    </AuthShell>
  )
}
