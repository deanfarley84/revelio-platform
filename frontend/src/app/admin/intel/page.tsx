'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { intelApi, adminApi, fmtCurrency } from '@/lib/api'

const STAGES = ['prospect','engaged','diagnostic_in_progress','report_delivered','follow_up','upsell_target','closed_won','closed_lost']

export default function IntelPage() {
  const [intel, setIntel] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [editing, setEditing] = useState<any>(null)
  const [logNote, setLogNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(()=>{ intelApi.list().then(r=>{setIntel(r.data);setLoading(false)}).catch(()=>setLoading(false)) },[])

  const selectClient = async (item:any) => {
    const r = await intelApi.get(item.org_id)
    setSelected(r.data); setEditing({...r.data}); setLogNote('')
  }

  const save = async () => {
    if(!editing) return
    setSaving(true)
    try {
      await intelApi.upsert(editing.org_id, {...editing, log_note: logNote||undefined})
      setLogNote('')
      const r = await intelApi.get(editing.org_id)
      setSelected(r.data); setEditing({...r.data})
      setIntel(prev=>prev.map(x=>x.org_id===editing.org_id?{...x,...editing}:x))
    } catch(e:any) { alert(e.response?.data?.detail||'Save failed') }
    setSaving(false)
  }

  const scoreColour = (s:number) => s>=75?'sr-h':s>=50?'sr-m':'sr-l'
  const scoreBg = (s:number) => s>=75?'bg-brand-green-bg text-brand-green':s>=50?'bg-brand-amber-bg text-brand-amber':'bg-brand-red-bg text-brand-red'

  if(loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading...</div></AppShell>

  return (
    <AppShell>
      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-5">
          <div><div className="section-title">Client intelligence</div><div className="section-sub">Private operator knowledge base — never shown to clients</div></div>
        </div>

        <div className="grid gap-4" style={{gridTemplateColumns: selected?'1fr 1.6fr':'1fr'}}>
          {/* Client list */}
          <div className="card">
            <div className="text-[12px] font-medium text-ink/50 mb-3 uppercase tracking-wider">All clients ({intel.length})</div>
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {intel.map((item:any)=>(
                <div key={item.org_id} onClick={()=>selectClient(item)}
                  className={`p-3 rounded-lg cursor-pointer transition-all border ${selected?.org_id===item.org_id?'border-brand-blue bg-brand-blue-bg':'border-transparent hover:bg-surface-2'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-[12.5px] font-medium truncate flex-1">{item.org_name}</div>
                    {item.score!=null&&<div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 ml-2 ${scoreBg(item.score)}`}>{item.score}</div>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10.5px] text-ink/40 capitalize">{item.opportunity_stage?.replace(/_/g,' ')}</span>
                    {item.total_leakage_identified&&<><span className="text-ink/20">·</span><span className="text-[10.5px] font-mono text-ink/50">{fmtCurrency(item.total_leakage_identified)}</span></>}
                    {item.tags?.slice(0,2).map((t:string)=><span key={t} className="tag tag-gray text-[9.5px]">{t}</span>)}
                  </div>
                </div>
              ))}
              {intel.length===0&&<p className="text-[12px] text-ink/40 py-6 text-center">No client intel records yet</p>}
            </div>
          </div>

          {/* Detail panel */}
          {selected&&editing&&(
            <div className="space-y-4">
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-[14px] font-medium">{selected.org_name}</div>
                    <div className="text-[11.5px] text-ink/40 mt-0.5">Client intelligence record · Operator-only</div>
                  </div>
                  <button onClick={save} disabled={saving} className="btn-primary btn-sm">{saving?'Saving...':'Save changes'}</button>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div><label className="label">Opportunity stage</label>
                    <select className="input" value={editing.opportunity_stage||''} onChange={e=>setEditing((p:any)=>({...p,opportunity_stage:e.target.value}))}>
                      {STAGES.map(s=><option key={s} value={s}>{s.replace(/_/g,' ')}</option>)}
                    </select>
                  </div>
                  <div><label className="label">Score (0–100)</label><input className="input" type="number" min="0" max="100" value={editing.score??''} onChange={e=>setEditing((p:any)=>({...p,score:parseInt(e.target.value)||null}))}/></div>
                  <div><label className="label">Follow-up date</label><input className="input" type="date" value={editing.follow_up_date||''} onChange={e=>setEditing((p:any)=>({...p,follow_up_date:e.target.value}))}/></div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div><label className="label">Contract renewal date</label><input className="input" type="date" value={editing.contract_renewal||''} onChange={e=>setEditing((p:any)=>({...p,contract_renewal:e.target.value}))}/></div>
                  <div><label className="label">Tags (comma separated)</label><input className="input" value={(editing.tags||[]).join(', ')} onChange={e=>setEditing((p:any)=>({...p,tags:e.target.value.split(',').map((s:string)=>s.trim()).filter(Boolean)}))}/></div>
                </div>

                <div className="mb-4"><label className="label">Operator notes</label>
                  <textarea className="input" rows={4} style={{resize:'none'}} value={editing.notes||''} onChange={e=>setEditing((p:any)=>({...p,notes:e.target.value}))} placeholder="Key contacts, relationship context, commercial intelligence, red flags, upsell signals..."/>
                </div>

                <div className="mb-4"><label className="label">Contract notes</label>
                  <textarea className="input" rows={3} style={{resize:'none'}} value={editing.contract_notes||''} onChange={e=>setEditing((p:any)=>({...p,contract_notes:e.target.value}))} placeholder="Contract structure, pricing model, renewal levers, negotiation notes..."/>
                </div>

                <div><label className="label">Upsell signals (comma separated)</label>
                  <input className="input" value={(editing.upsell_signals||[]).join(', ')} onChange={e=>setEditing((p:any)=>({...p,upsell_signals:e.target.value.split(',').map((s:string)=>s.trim()).filter(Boolean)}))} placeholder="Contract expires Dec 2025, FX exposure confirmed, CEO engaged..."/>
                </div>
              </div>

              {/* Activity log */}
              <div className="card">
                <div className="text-[13px] font-medium mb-3">Intelligence log</div>
                <div className="flex gap-2 mb-3">
                  <input className="input flex-1" value={logNote} onChange={e=>setLogNote(e.target.value)} placeholder="Add a note to the log (e.g. call outcome, new intel, follow-up action)..."/>
                  <button onClick={save} disabled={!logNote||saving} className="btn-primary btn-sm">Add note</button>
                </div>
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {(selected.log||[]).map((l:any)=>(
                    <div key={l.id} className="flex gap-2.5 py-2 border-b border-black/[0.04] last:border-0">
                      <div className="w-1.5 h-1.5 rounded-full bg-ink/20 mt-2 flex-shrink-0"/>
                      <div className="flex-1"><div className="text-[12px] text-ink/80">{l.note}</div><div className="text-[10.5px] text-ink/40 mt-0.5">{l.note_type} · {new Date(l.created_at).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}</div></div>
                    </div>
                  ))}
                  {(!selected.log||selected.log.length===0)&&<p className="text-[11.5px] text-ink/30 py-2">No log entries yet</p>}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
