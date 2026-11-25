import React, { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { AlertTriangle, Check, Pencil, Plus, Save, Trash2, X } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

function monthNow() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}` }
function money(currency, amount) { return new Intl.NumberFormat(undefined,{style:'currency',currency:currency||'INR',maximumFractionDigits:2}).format(Number(amount||0)) }

export default function BudgetsPage() {
  const { showToast, profile } = useOutletContext()
  const [month, setMonth] = useState(monthNow())
  const [budgets, setBudgets] = useState([])
  const [categories, setCategories] = useState([])
  const [category, setCategory] = useState('')
  const [limit, setLimit] = useState('')
  const [editingCategory, setEditingCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    Promise.all([apiRequest(`/budgets?month=${month}`), apiRequest('/transactions')])
      .then(([budgetResult, transactionResult]) => {
        if (active) { setBudgets(budgetResult.budgets); setCategories(transactionResult.categories) }
      })
      .catch(err => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [month, refresh])

  const alerts = budgets.filter(item => item.alert_level !== 'on_track')
  const resetForm = () => { setCategory(''); setLimit(''); setEditingCategory('') }
  function beginEdit(item) { setEditingCategory(item.category); setCategory(item.category); setLimit(String(item.limit)); document.querySelector('.budget-form')?.scrollIntoView({behavior:'smooth',block:'center'}) }

  async function save(event) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await apiRequest(`/budgets?month=${month}`, { method:'PUT', body:JSON.stringify({category,limit}) })
      showToast(editingCategory ? 'Budget updated.' : 'Monthly budget created.')
      resetForm(); setRefresh(value => value + 1)
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  async function remove(item) {
    if (!window.confirm(`Delete the ${item.category} budget for ${month}? Its transaction history will remain.`)) return
    setError('')
    try {
      await apiRequest(`/budgets?month=${month}`, { method:'DELETE', body:JSON.stringify({category:item.category}) })
      showToast('Budget deleted.'); if (editingCategory === item.category) resetForm(); setRefresh(value => value + 1)
    } catch (err) { setError(err.message) }
  }

  return <main className="finance-content">
    <div className="finance-page-title"><div><span className="eyebrow"><i/> SPENDING WITH INTENTION</span><h1>Monthly budgets</h1><p>Set category limits and follow spending against real transactions.</p></div><label className="budget-month-picker">Budget month<input aria-label="Budget month" type="month" value={month} onChange={e=>{setMonth(e.target.value);resetForm()}}/></label></div>
    {alerts.length>0 && <section className="budget-alert-summary" aria-live="polite"><AlertTriangle size={16}/><div><b>{alerts.length} budget {alerts.length===1?'needs':'need'} attention</b><span>{alerts.map(item=>`${item.category}: ${item.alert_message}`).join(' · ')}</span></div></section>}
    {error && <p className="auth-error budget-page-error" role="alert">{error}</p>}
    <section className="finance-panel budget-panel phase4-budget-form-panel"><div className="finance-panel-heading"><div><h2>{editingCategory?'Edit budget':'Create a category budget'}</h2><p>Each category has one limit for the selected month.</p></div></div>
      <form className="budget-form" onSubmit={save}>
        <label>Category<input list="phase4-budget-categories" value={category} onChange={e=>setCategory(e.target.value)} placeholder="e.g. Groceries" maxLength="60" readOnly={Boolean(editingCategory)} required/><datalist id="phase4-budget-categories">{categories.map(item=><option value={item} key={item}/>)}</datalist></label>
        <label>Monthly limit<input type="number" min="0" max="999999999.99" step="0.01" value={limit} onChange={e=>setLimit(e.target.value)} placeholder="0.00" required/></label>
        <button type="submit" className="button button-primary" disabled={saving}>{saving?<span>Saving…</span>:editingCategory?<><Save size={14}/> Update budget</>:<><Plus size={14}/> Set budget</>}</button>
        {editingCategory&&<button type="button" className="button button-outline cancel-budget-edit" onClick={resetForm}><X size={13}/> Cancel edit</button>}
      </form>
    </section>
    <section className="finance-panel budget-panel phase4-budget-list-panel">
      <div className="finance-panel-heading"><div><h2>Budget progress</h2><p>Spending is calculated from expense transactions dated in {month}.</p></div><span className="budget-count">{budgets.length} {budgets.length===1?'category':'categories'}</span></div>
      {loading?<div className="dashboard-loading"><span className="loading-mark">f.</span><span>Loading budgets and spending…</span></div>:error?<div className="dashboard-empty error-empty"><b>Budgets couldn’t be loaded.</b><button className="button button-outline" onClick={()=>setRefresh(v=>v+1)}>Try again</button></div>:budgets.length===0?<div className="dashboard-empty"><b>No budgets for {month} yet.</b><p>Create a category limit above to start tracking progress.</p></div>:<div className="phase4-budget-list">{budgets.map(item=>{const progress=Math.max(0,Math.min(item.usage_percent,100));return <article className={`phase4-budget-row ${item.alert_level}`} key={item.category}>
        <div className="phase4-budget-top"><div className="phase4-budget-title"><span className="phase4-category-dot"/><div><b>{item.category}</b><small>{money(profile.currency,item.spent)} spent of {money(profile.currency,item.limit)}</small></div></div><div className="phase4-budget-numbers"><div className="phase4-remaining"><small>{item.remaining<0?'Over by':'Remaining'}</small><b className={item.remaining<0?'over-budget':''}>{money(profile.currency,Math.abs(item.remaining))}</b></div><div className={`budget-status ${item.alert_level}`}>{item.alert_level==='on_track'?'On track':item.alert_level==='warning'?'80% warning':item.alert_level==='reached'?'Limit reached':'Exceeded'}</div><button aria-label={`Edit ${item.category} budget`} onClick={()=>beginEdit(item)}><Pencil size={14}/></button><button className="remove-budget" aria-label={`Delete ${item.category} budget`} onClick={()=>remove(item)}><Trash2 size={14}/></button></div></div>
        <div className="budget-progress phase4-progress"><span className={item.alert_level} style={{width:`${progress}%`}}/></div><div className="phase4-budget-foot"><span>{Math.round(item.usage_percent)}% used</span>{item.alert_message&&<span className={`phase4-alert-message ${item.alert_level}`}><AlertTriangle size={12}/>{item.alert_message}</span>}</div>
      </article>})}</div>}
    </section>
    <div className="budget-threshold-note"><span><i className="threshold-dot safe"/>Under 80%</span><span><i className="threshold-dot warning"/>80% warning</span><span><i className="threshold-dot reached"/>100% reached</span><span><i className="threshold-dot exceeded"/>Over budget</span></div>
  </main>
}
