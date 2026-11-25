import React, { useEffect, useState } from 'react'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import { AlertCircle, CalendarDays, Download, TrendingUp } from 'lucide-react'
import { apiRequest, API_BASE } from '../lib/api.js'

const dateOptions = [
  ['last_7_days','Last 7 days'], ['last_30_days','Last 30 days'], ['this_month','This month'], ['last_month','Last month'], ['custom','Custom range'],
]
const palette = ['#8c73ff','#5a80ff','#55c9a5','#e7a06c','#d777a0','#6dbedb','#b3a5e0','#d2c06e']
function money(currency,value) { return new Intl.NumberFormat(undefined,{style:'currency',currency:currency||'INR',maximumFractionDigits:2}).format(Number(value||0)) }
function shortDate(value) { const date=new Date(`${value}T12:00:00`); return new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric'}).format(date) }
function shortMonth(value) { const [year,month]=value.split('-').map(Number); return new Intl.DateTimeFormat(undefined,{month:'short',year:'2-digit'}).format(new Date(year,month-1,1)) }
function chartOptions(currency) { return {responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{usePointStyle:true,pointStyle:'circle',boxWidth:7,color:'#aaa6b4',font:{size:9,family:'DM Sans'}}},tooltip:{backgroundColor:'#191821',borderColor:'rgba(255,255,255,.1)',borderWidth:1,padding:9,titleColor:'#f2effa',bodyColor:'#c3bdce',callbacks:{label:ctx=>`${ctx.dataset.label}: ${money(currency,ctx.raw)}`}}},scales:{x:{grid:{display:false},border:{display:false},ticks:{color:'#777482',maxTicksLimit:9,font:{size:8}}},y:{beginAtZero:true,grid:{color:'rgba(255,255,255,.055)'},border:{display:false},ticks:{color:'#777482',font:{size:8},callback:value=>money(currency,value)}}}} }

function AnalyticsCharts({report}) {
  const options=chartOptions(report.currency)
  const trend=report.trend||[]
  const monthly=report.monthly_reports||[]
  const categories=report.category_expenses||[]
  const line={labels:trend.map(row=>shortDate(row.date)),datasets:[{label:'Income',data:trend.map(row=>row.income),borderColor:'#9278ff',backgroundColor:'rgba(146,120,255,.08)',fill:true,tension:.34,pointRadius:2},{label:'Expenses',data:trend.map(row=>row.expenses),borderColor:'#5f89ff',backgroundColor:'rgba(95,137,255,.04)',fill:false,tension:.34,pointRadius:2}]}
  const bar={labels:monthly.map(row=>shortMonth(row.month)),datasets:[{label:'Monthly income',data:monthly.map(row=>row.income),backgroundColor:'rgba(143,116,255,.72)',borderRadius:4,maxBarThickness:24},{label:'Monthly expenses',data:monthly.map(row=>row.expenses),backgroundColor:'rgba(80,132,255,.72)',borderRadius:4,maxBarThickness:24}]}
  const savings={labels:monthly.map(row=>shortMonth(row.month)),datasets:[{label:'Net savings',data:monthly.map(row=>row.savings),borderColor:'#64c99a',backgroundColor:'rgba(100,201,154,.1)',fill:true,tension:.32,pointRadius:2}]}
  const donutOptions={responsive:true,maintainAspectRatio:false,cutout:'70%',plugins:{legend:{position:'bottom',labels:{color:'#aaa6b4',padding:12,usePointStyle:true,pointStyle:'circle',boxWidth:7,font:{size:8}}},tooltip:options.plugins.tooltip}}
  return <div className="finance-charts-grid phase4-analytics-charts"><section className="finance-panel chart-panel"><div className="finance-panel-heading"><div><h2>Income vs. expenses</h2><p>Daily cash flow within this date range</p></div></div><div className="finance-chart"><Line data={line} options={options}/></div></section><section className="finance-panel chart-panel"><div className="finance-panel-heading"><div><h2>Monthly reports</h2><p>Income and expenses by month</p></div></div><div className="finance-chart"><Bar data={bar} options={options}/></div></section><section className="finance-panel chart-panel"><div className="finance-panel-heading"><div><h2>Category-wise expenses</h2><p>Expense share in this date range</p></div></div>{categories.length?<div className="finance-donut"><Doughnut data={{labels:categories.map(item=>item.category),datasets:[{data:categories.map(item=>item.amount),backgroundColor:categories.map((_,index)=>palette[index%palette.length]),borderWidth:0,spacing:3,borderRadius:4}]}} options={donutOptions}/></div>:<div className="analytics-no-chart">No expense categories for this range.</div>}</section><section className="finance-panel chart-panel"><div className="finance-panel-heading"><div><h2>Savings trend</h2><p>Monthly income after expenses</p></div></div><div className="finance-chart"><Line data={savings} options={options}/></div></section></div>
}

export default function AnalyticsPage() {
  const [range,setRange]=useState('this_month')
  const [dateFrom,setDateFrom]=useState('')
  const [dateTo,setDateTo]=useState('')
  const [applied,setApplied]=useState({range:'this_month'})
  const [report,setReport]=useState(null)
  const [loading,setLoading]=useState(true)
  const [exporting,setExporting]=useState(false)
  const [error,setError]=useState('')
  const [exportError,setExportError]=useState('')
  useEffect(()=>{let active=true;setLoading(true);setError('');const query=new URLSearchParams(applied);apiRequest(`/analytics?${query}`).then(data=>{if(active)setReport(data)}).catch(err=>{if(active)setError(err.message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[applied])

  function selectRange(value) { setRange(value); setExportError(''); if(value!=='custom')setApplied({range:value}) }
  function applyCustom(event) { event.preventDefault();setExportError('');if(!dateFrom||!dateTo||dateFrom>dateTo){setError('Choose a valid custom date range.');return}setError('');setApplied({range:'custom',date_from:dateFrom,date_to:dateTo}) }
  async function exportCsv() {
    setExporting(true);setExportError('')
    try {
      const query=new URLSearchParams(applied)
      const response=await fetch(`${API_BASE}/analytics/export?${query}`,{credentials:'include'})
      if(!response.ok){let data={};try{data=await response.json()}catch{};throw new Error(data.error||'The report could not be exported.')}
      const blob=await response.blob()
      const disposition=response.headers.get('content-disposition')||''
      const filename=disposition.match(/filename="?([^";]+)"?/i)?.[1]||'finsight-report.csv'
      const objectUrl=URL.createObjectURL(blob)
      const link=document.createElement('a');link.href=objectUrl;link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(objectUrl),1000)
    } catch(err) { setExportError(err.message) }
    finally { setExporting(false) }
  }

  return <main className="finance-content"><div className="finance-page-title"><div><span className="eyebrow"><i/> YOUR MONEY, IN PERSPECTIVE</span><h1>Financial analytics</h1><p>Income, spending, and savings trends from your saved transactions.</p></div><button className="button button-primary phase4-export-button" onClick={exportCsv} disabled={exporting||loading||!report}><Download size={14}/>{exporting?'Preparing CSV…':'Export CSV'}</button></div>
    <section className="finance-panel analytics-filter-panel"><div className="analytics-range-buttons">{dateOptions.map(([value,label])=><button key={value} type="button" className={range===value?'selected':''} onClick={()=>selectRange(value)}>{label}</button>)}</div>{range==='custom'&&<form className="analytics-custom-range" onSubmit={applyCustom}><label>From<input type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)} required/></label><span>to</span><label>To<input type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)} required/></label><button className="button button-outline" type="submit">Apply range</button></form>}</section>
    {(error||exportError)&&<div className="phase4-analytics-error" role="alert"><AlertCircle size={14}/>{error||exportError}{error&&<button onClick={()=>setApplied({...applied})}>Retry</button>}</div>}
    {loading?<div className="dashboard-loading"><span className="loading-mark">f.</span><span>Loading analytics from your transactions…</span></div>:error?null:report&&<>
      <div className="phase4-report-period"><CalendarDays size={13}/><span>{new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',year:'numeric'}).format(new Date(`${report.date_from}T12:00:00`))} – {new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',year:'numeric'}).format(new Date(`${report.date_to}T12:00:00`))}</span><span>{report.summary.transaction_count} transactions</span></div>
      <div className="analytics-highlights phase4-report-highlights"><div><span>Income</span><b>{money(report.currency,report.summary.income)}</b><small>For selected dates</small></div><div><span>Expenses</span><b>{money(report.currency,report.summary.expenses)}</b><small>For selected dates</small></div><div><span>Net savings</span><b className={report.summary.savings>=0?'report-positive':'report-negative'}>{money(report.currency,report.summary.savings)}</b><small>Income minus expenses</small></div><div><span>Savings percentage</span><b className={report.summary.savings_percentage>=0?'report-positive':'report-negative'}>{report.summary.savings_percentage.toFixed(2)}%</b><small>Of income in this range</small></div></div>
      <AnalyticsCharts report={report}/>
      <div className="phase4-analytics-bottom"><section className="finance-panel phase4-report-table"><div className="finance-panel-heading"><div><h2>Monthly income and expense reports</h2><p>Each month within the selected range</p></div></div>{report.monthly_reports.length?<div className="transaction-table-wrap"><table className="transaction-table"><thead><tr><th>MONTH</th><th>INCOME</th><th>EXPENSES</th><th>NET SAVINGS</th><th>SAVINGS %</th></tr></thead><tbody>{report.monthly_reports.map(row=><tr key={row.month}><td>{shortMonth(row.month)}</td><td className="transaction-value income">{money(report.currency,row.income)}</td><td>{money(report.currency,row.expenses)}</td><td className={row.savings>=0?'report-positive':'report-negative'}>{money(report.currency,row.savings)}</td><td>{row.savings_percentage.toFixed(2)}%</td></tr>)}</tbody></table></div>:<p className="analytics-no-chart">No monthly data in this date range.</p>}</section><section className="finance-panel phase4-highest-panel"><div className="finance-panel-heading"><div><h2>Highest spending categories</h2><p>Ranked by actual expense totals</p></div><TrendingUp size={15}/></div>{report.highest_spending_categories.length?<div className="highest-category-list">{report.highest_spending_categories.map((item,index)=>{const percent=report.summary.expenses?item.amount/report.summary.expenses*100:0;return <div className="highest-category" key={item.category}><div className="highest-category-head"><span><i style={{background:palette[index%palette.length]}}/>{item.category}</span><b>{money(report.currency,item.amount)}</b></div><div className="budget-progress"><span style={{width:`${Math.min(percent,100)}%`,background:palette[index%palette.length]}}/></div><small>{percent.toFixed(1)}% of expenses</small></div>})}</div>:<p className="analytics-no-chart">No expenses in this date range.</p>}</section></div>
    </>}
  </main>
}
