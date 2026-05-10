'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { adminApi, fmtCurrency } from '@/lib/api'
import Link from 'next/link'
import { AlertTriangle, CheckCircle, Clock, Users, TrendingUp, Flag } from 'lucide-react'

export default function AdminPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  useEffect(()=>{adminApi.overview().then(r=>{setData(r.data);setLoading(false)}).catch(()=>setLoading(false))},[])
  if(loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading...</div></AppShell>
  const stats=data?.stats||{}; const pipeline=data?.pipeline||[]; const top=data?.top_opportunities||[]
  const stageTag=(s:string)=>{
    if(['released','approved'].includes(s)) return <span className="tag tag-green text-[10px]">Released</span>
    if(s==='pending_review') return <Link href="/admin/queue"><span className="tag tag-amber text-[10px]">Review</span></Link>
    if(['submitted','processing','ai_complete'].includes(s)) return <span className="tag tag-blue text-[10px]">Processing</span>
    if(s==='revision_requested') return <span className="tag tag-red text-[10px]">Flagged</span>
    return <span className="tag tag-gray text-[10px]">{s}</span>
  }
  return (
    <AppShell>
      <div className="max-w-6xl">
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            {label:'Active clients',value:stats.active_clients??'—',sub:'organisations',icon:<Users size={14}/>,cls:'text-brand-blue'},
            {label:'Pending approval',value:stats.pending_approval??0,sub:'awaiting review',icon:<Clock size={14}/>,cls:'text-brand-amber',alert:stats.pending_approval>0},
            {label:'Total leakage identified',value:fmtCurrency(stats.total_leakage_identified),sub:'all clients',icon:<TrendingUp size={14}/>,cls:'text-brand-green'},
            {label:'Low confidence flags',value:stats.low_confidence_flags??0,sub:'data gaps',icon:<Flag size={14}/>,cls:'text-brand-red',alert:(stats.low_confidence_flags??0)>0},
          ].map(({label,value,sub,icon,cls,alert})=>(
            <div key={label} className="kpi-card">
              <div className="flex items-center justify-between mb-2"><div className="kpi-label">{label}</div><div className={cls}>{icon}</div></div>
              <div className={`kpi-value ${alert?'text-brand-amber':''}`}>{value}</div>
              <div className="text-[11px] text-ink/40 mt-1.5">{sub}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="card">
            <div className="flex items-center justify-between mb-4"><div className="text-[13px] font-medium">Pipeline status</div><Link href="/admin/pipeline" className="text-[11.5px] text-brand-blue">View all →</Link></div>
            {pipeline.slice(0,7).map((d:any)=>(
              <div key={d.id} className="flex items-center gap-3 py-2.5 border-b border-black/[0.05] last:border-0">
                <div className="flex-1 min-w-0">
                  <div className="text-[12.5px] font-medium truncate flex items-center gap-1.5">
                    <span className="truncate">{d.company_name}</span>
                    {d.is_demo && <span className="tag tag-amber text-[9.5px] shrink-0">DEMO</span>}
                  </div>
                  <div className="text-[11px] text-ink/40">{d.tier?.toUpperCase()} · {d.submitted_at?new Date(d.submitted_at).toLocaleDateString('en-GB',{day:'numeric',month:'short'}):''}</div>
                </div>
                {stageTag(d.status)}
              </div>
            ))}
            {pipeline.length===0&&<p className="text-[12px] text-ink/40 py-4 text-center">No active diagnostics</p>}
          </div>
          <div className="card">
            <div className="flex items-center justify-between mb-4"><div className="text-[13px] font-medium">Top leakage opportunities</div><div className="text-[11px] text-ink/40">Mid estimate</div></div>
            <table className="tbl">
              <thead><tr><th>Client</th><th>Tier</th><th>Est. leakage</th><th>Status</th></tr></thead>
              <tbody>
                {top.slice(0,6).map((d:any)=>(
                  <tr key={d.id}>
                    <td className="font-medium">
                      <span className="inline-flex items-center gap-1.5">
                        {d.org_name||d.company_name}
                        {d.is_demo && <span className="tag tag-amber text-[9.5px]">DEMO</span>}
                      </span>
                    </td>
                    <td><span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span></td>
                    <td className="font-mono">{fmtCurrency(d.leakage_mid)}</td>
                    <td className="capitalize text-ink/60 text-[11px]">{d.status?.replace(/_/g,' ')}</td>
                  </tr>
                ))}
                {top.length===0&&<tr><td colSpan={4} className="text-center text-ink/40 py-4">No data</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="card">
            <div className="text-[13px] font-medium mb-4">Diagnostics by stage</div>
            {[{label:'Released',count:stats.released||0,pct:87,color:'bg-brand-green'},{label:'Pending review',count:stats.pending_approval||0,pct:25,color:'bg-brand-amber'},{label:'Processing',count:stats.processing||0,pct:33,color:'bg-brand-blue'}].map(({label,count,pct,color})=>(
              <div key={label} className="flex items-center gap-2.5 mb-3 last:mb-0">
                <span className="text-[12px] flex-1 text-ink/70">{label}</span>
                <div className="flex-[2] h-1.5 bg-surface-2 rounded-full overflow-hidden"><div className={`h-full rounded-full ${color}`} style={{width:`${pct}%`}}/></div>
                <span className="text-[12px] font-mono w-5 text-right text-ink/60">{count}</span>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="text-[13px] font-medium mb-4">Alerts</div>
            <div className="space-y-2">
              {(stats.pending_approval??0)>0&&<div className="alert-amber text-[11.5px]"><AlertTriangle size={12}/>{stats.pending_approval} awaiting approval</div>}
              {(stats.low_confidence_flags??0)>0&&<div className="alert-red text-[11.5px]"><Flag size={12}/>{stats.low_confidence_flags} low-confidence submission{stats.low_confidence_flags>1?'s':''}</div>}
              {(stats.pending_approval??0)===0&&(stats.low_confidence_flags??0)===0&&<div className="alert-green text-[11.5px]"><CheckCircle size={12}/>All clear</div>}
            </div>
          </div>
          <div className="card">
            <div className="text-[13px] font-medium mb-4">Quick actions</div>
            <div className="space-y-2">
              {[{l:`Approval queue (${stats.pending_approval||0})`,h:'/admin/queue'},{l:'Client intelligence',h:'/admin/intel'},{l:'Benchmarks',h:'/admin/benchmarks'},{l:'Pipeline',h:'/admin/pipeline'},{l:'All clients',h:'/admin/clients'}].map(({l,h})=>(
                <Link key={h} href={h} className="btn-ghost w-full justify-between text-left text-[12px]">{l} →</Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
