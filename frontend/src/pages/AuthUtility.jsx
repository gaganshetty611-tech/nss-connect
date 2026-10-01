import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../services/api'
import authService from '../services/authService'
import { ErrorAlert, Field, InfoAlert, Spinner } from '../components/ui'
import { useSpamGuard } from '../utils/spam'
import { AuthShell } from './Login'

export function ForgotPassword() {
  const [sent, setSent] = useState(null)
  const [error, setError] = useState(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({ mode: 'onTouched' })
  const { honeypot, isBot } = useSpamGuard(register)
  const onSubmit = async (values) => {
    setError(null)
    if (isBot(values)) return setError('Please wait a moment and try again.')
    const { email } = values
    try {
      setSent((await authService.forgotPassword(email)).detail)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  return (
    <AuthShell title="Forgot password" subtitle="We'll email you a secure reset link.">
      {sent ? (
        <InfoAlert tone="success">{sent}</InfoAlert>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <ErrorAlert message={error} />
          {honeypot}
          <Field label="Email" error={errors.email?.message}>
            <input className="input" type="email" autoComplete="email" {...register('email', { required: 'Email is required', pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email address' } })} />
          </Field>
          <button className="btn-primary w-full" disabled={isSubmitting}>Send reset link</button>
        </form>
      )}
      <p className="mt-4 text-center text-sm"><Link to="/login" className="text-brand-700">Back to login</Link></p>
    </AuthShell>
  )
}

export function ResetPassword() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState(null)
  const [done, setDone] = useState(null)
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm()
  const uid = params.get('uid')
  const token = params.get('token')
  const onSubmit = async ({ password }) => {
    setError(null)
    try {
      setDone((await authService.resetPassword(uid, token, password)).detail)
      setTimeout(() => navigate('/login'), 2500)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  if (!uid || !token) return <AuthShell title="Reset password"><ErrorAlert message="This reset link is incomplete. Request a new one." /></AuthShell>
  return (
    <AuthShell title="Choose a new password">
      {done ? (
        <InfoAlert tone="success">{done}</InfoAlert>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <ErrorAlert message={error} />
          <Field label="New password" error={errors.password?.message}>
            <input className="input" type="password" autoComplete="new-password" {...register('password', { required: 'Required', minLength: { value: 8, message: 'At least 8 characters' } })} />
          </Field>
          <Field label="Confirm password" error={errors.confirm?.message}>
            <input className="input" type="password" autoComplete="new-password" {...register('confirm', { validate: (v) => v === watch('password') || 'Passwords do not match' })} />
          </Field>
          <button className="btn-primary w-full" disabled={isSubmitting}>Update password</button>
        </form>
      )}
    </AuthShell>
  )
}

export function VerifyEmail() {
  const [params] = useSearchParams()
  const [state, setState] = useState({ loading: true })
  const ran = useRef(false)
  useEffect(() => {
    if (ran.current) return
    ran.current = true
    const uid = params.get('uid')
    const token = params.get('token')
    if (!uid || !token) return setState({ error: 'This verification link is incomplete.' })
    authService
      .verifyEmail(uid, token)
      .then((d) => setState({ message: d.detail }))
      .catch((e) => setState({ error: errorMessage(e) }))
  }, [params])
  return (
    <AuthShell title="Email verification">
      {state.loading && <Spinner label="Verifying…" />}
      {state.message && <InfoAlert tone="success">{state.message}</InfoAlert>}
      <ErrorAlert message={state.error} />
      {!state.loading && <Link to="/login" className="btn-primary mt-6 w-full">Go to login</Link>}
    </AuthShell>
  )
}

export function GoogleCallback() {
  const [params] = useSearchParams()
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState(null)
  const ran = useRef(false)
  useEffect(() => {
    if (ran.current) return
    ran.current = true
    const expected = sessionStorage.getItem('google_oauth_state')
    sessionStorage.removeItem('google_oauth_state')
    if (!params.get('code') || params.get('state') !== expected) {
      setError('Google sign-in was cancelled or the response could not be validated.')
      return
    }
    loginWithGoogle(params.get('code'))
      .then(() => navigate('/dashboard', { replace: true }))
      .catch((e) => setError(errorMessage(e)))
  }, [params, loginWithGoogle, navigate])
  return (
    <AuthShell title="Signing in with Google">
      {error ? <ErrorAlert message={error} /> : <Spinner label="Completing sign-in…" />}
      {error && <Link to="/login" className="btn-secondary mt-4 w-full">Back to login</Link>}
    </AuthShell>
  )
}
