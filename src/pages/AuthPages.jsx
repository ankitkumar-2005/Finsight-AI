import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, LockKeyhole, Sparkles } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

function AuthFrame({ children }) {
  return <div className="auth-page"><div className="auth-glow auth-glow-a"/><div className="auth-glow auth-glow-b"/><header className="auth-header"><a className="brand" href="/"><span className="brand-mark"><span/><span/><span/></span><span>fin<span className="brand-accent">sight</span></span></a><Link to="/" className="auth-back">← Back to home</Link></header><main className="auth-main">{children}<p className="auth-foot">Thoughtful money management, powered by FinSight AI</p></main></div>
}

function AuthCard({ children }) {
  return <div className="auth-card"><div className="auth-orb"><Sparkles size={22}/></div><span className="eyebrow"><i/> A LITTLE MORE CLARITY</span>{children}<div className="auth-secure"><LockKeyhole size={12}/> Your information is encrypted and secure.</div></div>
}

function FieldError({ children }) { return children ? <small className="field-error">{children}</small> : null }

export function SignupPage({ showToast }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  async function submit(event) {
    event.preventDefault()
    setError(''); setFieldErrors({}); setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      await apiRequest('/auth/register', { method: 'POST', body: JSON.stringify({ name: data.get('name'), email: data.get('email'), password: data.get('password') }) })
      showToast('Your account is ready. Welcome to FinSight!')
      navigate('/dashboard', { replace: true })
    } catch (err) { setError(err.message); setFieldErrors(err.fieldErrors || {}) }
    finally { setBusy(false) }
  }
  return <AuthFrame><AuthCard><h1>Your money, meet FinSight.</h1><p className="auth-sub">Create your account and take the first step toward feeling good about money.</p><form onSubmit={submit} className="auth-form"><label>Your name<input name="name" autoComplete="name" placeholder="Olivia Martin" required minLength="2" maxLength="100"/><FieldError>{fieldErrors.name}</FieldError></label><label>Email address<input type="email" name="email" autoComplete="email" placeholder="you@example.com" required maxLength="254"/><FieldError>{fieldErrors.email}</FieldError></label><label>Password<div className="password-field"><input type={showPassword?'text':'password'} name="password" autoComplete="new-password" placeholder="At least 8 characters" required minLength="8" maxLength="128"/><button type="button" onClick={()=>setShowPassword(!showPassword)}>{showPassword?'Hide':'Show'}</button></div><FieldError>{fieldErrors.password}</FieldError></label><label className="consent"><input type="checkbox" required/><span>I agree to FinSight's <a href="/#about">Terms</a> and <a href="/#about">Privacy Policy</a>.</span></label><FieldError>{fieldErrors.consent}</FieldError>{error&&<p className="auth-error" role="alert">{error}</p>}<button type="submit" className="button button-primary auth-submit" disabled={busy}>{busy?'Creating account…':'Create my account'} {!busy&&<ArrowRight size={15}/>}</button></form><div className="auth-switch">Already have an account? <Link to="/login">Log in</Link></div></AuthCard></AuthFrame>
}

export function LoginPage({ showToast }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      await apiRequest('/auth/login', { method: 'POST', body: JSON.stringify({ email: data.get('email'), password: data.get('password') }) })
      showToast('Welcome back to FinSight.')
      navigate('/dashboard', { replace: true })
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <AuthFrame><AuthCard><h1>Welcome back.</h1><p className="auth-sub">Log in to pick up where you left off.</p><form onSubmit={submit} className="auth-form"><label>Email address<input type="email" name="email" autoComplete="email" placeholder="you@example.com" required maxLength="254"/></label><label>Password<div className="password-field"><input type={showPassword?'text':'password'} name="password" autoComplete="current-password" placeholder="Your password" required/><button type="button" onClick={()=>setShowPassword(!showPassword)}>{showPassword?'Hide':'Show'}</button></div></label><div className="forgot-row"><Link to="/forgot-password">Forgot password?</Link></div>{error&&<p className="auth-error" role="alert">{error}</p>}<button type="submit" className="button button-primary auth-submit" disabled={busy}>{busy?'Logging in…':'Log in'} {!busy&&<ArrowRight size={15}/>}</button></form><div className="auth-switch">New to FinSight? <Link to="/signup">Get started free</Link></div></AuthCard></AuthFrame>
}

export function ForgotPasswordPage({ showToast }) {
  const [token, setToken] = useState('')
  const [demoToken, setDemoToken] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function requestReset(event) {
    event.preventDefault(); setError(''); setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      const result = await apiRequest('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email: data.get('email') }) })
      setSent(true); if (result.demo_reset_token) setDemoToken(result.demo_reset_token)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  async function resetPassword(event) {
    event.preventDefault(); setError(''); setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      await apiRequest('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token: data.get('token'), password: data.get('password') }) })
      showToast('Password updated. You can log in with your new password.')
      window.location.assign('/login')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <AuthFrame><AuthCard><h1>{sent?'Set a new password.':'Forgot your password?'}</h1><p className="auth-sub">{sent?'Use the one-time reset token to choose a new password.':'Enter your account email to start a safe password reset.'}</p>{!sent?<form onSubmit={requestReset} className="auth-form"><label>Email address<input type="email" name="email" autoComplete="email" placeholder="you@example.com" required maxLength="254"/></label>{error&&<p className="auth-error" role="alert">{error}</p>}<button className="button button-primary auth-submit" disabled={busy}>{busy?'Preparing…':'Send reset instructions'} {!busy&&<ArrowRight size={15}/>}</button></form>:<form onSubmit={resetPassword} className="auth-form">{demoToken&&<div className="demo-reset-note"><b>Development demo token</b><span>This one-time token expires in 20 minutes. In production, the token is sent through a configured email provider.</span></div>}<label>Reset token<input name="token" autoComplete="one-time-code" placeholder="Paste your reset token" value={token} onChange={e=>setToken(e.target.value)} required minLength="32"/></label>{demoToken&&<button type="button" className="copy-token" onClick={()=>setToken(demoToken)}>Use demo token</button>}<label>New password<input type="password" name="password" autoComplete="new-password" placeholder="At least 8 characters" required minLength="8" maxLength="128"/></label>{error&&<p className="auth-error" role="alert">{error}</p>}<button className="button button-primary auth-submit" disabled={busy}>{busy?'Updating…':'Update password'} {!busy&&<ArrowRight size={15}/>}</button></form>}<div className="auth-switch"><Link to="/login">Back to log in</Link></div></AuthCard></AuthFrame>
}
