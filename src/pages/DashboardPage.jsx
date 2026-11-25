import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, LogOut, Save, ShieldCheck, Wallet } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

export function ProtectedRoute({ children }) {
  const [state, setState] = useState('checking')
  useEffect(() => { let active = true; apiRequest('/auth/me').then(()=>{if(active)setState('ready')}).catch(()=>{if(active)setState('unauthorized')}); return ()=>{active=false} }, [])
  if (state === 'checking') return <main className="protected-loading"><span className="loading-mark">f.</span><p>Opening your secure space…</p></main>
  if (state === 'unauthorized') return <Navigate to="/login" replace />
  return children
}

const emptyProfile = { currency: 'INR', monthly_income: 0, savings_goal: 0 }
export default function DashboardPage({ showToast }) {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(emptyProfile)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([apiRequest('/auth/me'), apiRequest('/profile/me')]).then(([auth, financial])=>{ if(active){setUser(auth.user);setProfile(financial.profile)} }).catch(err=>{if(active)setError(err.message)})
    return ()=>{active=false}
  }, [])
  async function saveProfile(event) {
    event.preventDefault(); setBusy(true); setError('')
    const data = new FormData(event.currentTarget)
    try { const result=await apiRequest('/profile/me',{method:'PUT',body:JSON.stringify({currency:data.get('currency'),monthly_income:data.get('monthly_income'),savings_goal:data.get('savings_goal')})}); setProfile(result.profile); showToast('Your financial profile is saved.') }
    catch(err){setError(err.message)} finally{setBusy(false)}
  }
  async function logout() {
    try { await apiRequest('/auth/logout',{method:'POST'}); showToast('You have been logged out.'); navigate('/',{replace:true}) }
    catch(err){setError(err.message)}
  }
  const money = amount => new Intl.NumberFormat(undefined,{style:'currency',currency:profile.currency,maximumFractionDigits:2}).format(Number(amount||0))
  return <div className="account-page"><header className="account-header"><a className="brand" href="/"><span className="brand-mark"><span/><span/><span/></span><span>fin<span className="brand-accent">sight</span></span></a><div className="account-header-right"><span className="account-avatar">{user?.name?.trim()?.[0]?.toUpperCase()||'F'}</span><span className="account-user">{user?.name||'Your account'}</span><button className="button button-outline logout-button" onClick={logout}><LogOut size={14}/> Log out</button></div></header><main className="account-main"><div className="account-welcome"><span className="eyebrow"><i/> YOUR PRIVATE FINANCIAL SPACE</span><h1>Good to see you, <span className="gradient-text">{user?.name?.split(' ')[0]||'friend'}.</span></h1><p>Your account is secure. Add your financial profile to start shaping your dashboard.</p></div>{error&&<p className="auth-error account-error" role="alert">{error}</p>}<div className="account-grid"><section className="account-panel profile-panel"><div className="panel-heading"><span className="feature-icon"><Wallet size={18}/></span><div><h2>Your financial profile</h2><p>Only you can access and update these details.</p></div></div><form className="profile-form" onSubmit={saveProfile}><label>Currency<select name="currency" value={profile.currency} onChange={e=>setProfile({...profile,currency:e.target.value})}><option value="INR">INR — Indian Rupee</option><option value="USD">USD — US Dollar</option><option value="EUR">EUR — Euro</option><option value="GBP">GBP — British Pound</option></select></label><label>Monthly income<input type="number" inputMode="decimal" name="monthly_income" min="0" max="999999999.99" step="0.01" value={profile.monthly_income} onChange={e=>setProfile({...profile,monthly_income:e.target.value})} required/></label><label>Savings goal<input type="number" inputMode="decimal" name="savings_goal" min="0" max="999999999.99" step="0.01" value={profile.savings_goal} onChange={e=>setProfile({...profile,savings_goal:e.target.value})} required/></label><button type="submit" className="button button-primary" disabled={busy}>{busy?'Saving…':'Save profile'} {!busy&&<Save size={14}/>}</button></form></section><section className="account-panel snapshot-panel"><div className="panel-heading"><span className="feature-icon"><ShieldCheck size={18}/></span><div><h2>Your snapshot</h2><p>A private summary from your saved profile.</p></div></div><div className="snapshot-values"><div><span>Monthly income</span><b>{money(profile.monthly_income)}</b></div><div><span>Savings goal</span><b>{money(profile.savings_goal)}</b></div><div><span>Currency</span><b>{profile.currency}</b></div></div><div className="snapshot-note"><ShieldCheck size={15}/><span>Your financial details are attached to your account and protected by your session.</span></div><a className="text-link" href="/#features">Explore FinSight tools <ArrowRight size={14}/></a></section></div><a className="account-home" href="/">← Back to FinSight home</a></main></div>
}
