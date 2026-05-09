'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { adminApi, diagnosticsApi, fmtCurrency, confidenceColour } from '@/lib/api'
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react'

export default function QueuePage() {
  const [queue, setQueue] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [approving, setApproving] = useState<string|null>(null)
  const [notes, setNotes] = useState<Record<string,string>>({})
  const [overrides, setOverrides] = useState<Record<string,{low:string,mid:string,high:string,reason:string}>>({})

  useEffect(()=>{adminApi.queue().then(r=>{setQueue(r.data);setLoading(false)}).catch(()=>setLoading(false))},[])

  const approve = async (d:any) => {
    setApproving(d.id)
    try {
      const ov = overrides[d.id]
      const payload:any = { operator_notes: notes[d.id]||'' }
      if(ov?.mid) {
        payload.override_enabled=true; payload.override_low=parseFloat(ov.low||'0'); payload.override_mid=parseFloat(ov.mid||'0'); payload.override_high=parseFloat(ov.high||'0'); payload.override_reason=ov.reason||''
      }
      await diagnosticsApi.approve(d.id, payload)
      setQueue(q=>q.filter(x=>x.id!==d.id))
    } catch(e:any) { alert(e.response?.data?.detail||'Approval failed') }
    setApproving(null)
  }

  const reject = async (d:any) => {
    const reason = prompt('Reason for requesting additional data:')
    if(!reason) return
    try { await diagnosticsApi.reject(d.id,{reason, notes: notes[d.id]||''}); setQueue(q=>q.filter(x=>x.id!==d.id)) }
    catch(e:any) { alert(e.response?.data?.detail||'Failed') }
  }

  const setNote = (id:string,v:string) => setNotes(p=>({...p,[id]:v}))
  const setOvr = (id:string,k:string,v:string) => setOverrides(p=>({...p,[id]:{...(p[id]||{low:'',mid:'',high:'',reason:''}), [k]:v}}))

  if(loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading queue...</div></AppShell>

  return (
    <AppShell>
      <div className="max-w-5xl">
        <div className="flex items-center justify-between mb-5">
          <div><div className="section-title">Approval queue</div><div className="section-sub">{queue.length} diagnostic{queue.length!==1?'s':''} pending your review</div></div>
        </div>
        {queue.length===0&&(
          <div className="card text-center py-12">
            <CheckCircle size={28} className="text-brand-green mx-auto mb-3"/>
            <div className="text-[13px] font-medium mb-1">Queue clear</div>
            <div className="text-[12px] text-ink/50">No diagnostics awaiting approval.</div>
          </div>
        )}
        <div className="space-y-4">
          {queue.map((d:any)=>{
            const ai=d.ai_output||{}; const est=ai.annual_leakage_estimate||{}; const ov=overrides[d.id]||{low:'',mid:'',high:'',reason:''}
            const isLowConf=ai.confidence_level==='low'
            return (
              <div key={d.id} className="card">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <div className="text-[14px] font-medium">{d.company_name}</div>
                      <span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span>
                      <span className={`tag ${isLowConf?'tag-red':'tag-amber'}`}>{isLowConf?'Low confidence':'Pending approval'}</span>
                      <span className={`text-[11.5px] font-medium ${confidenceColour(ai.confidence_level)}`}>Confidence: {ai.confidence_level||'—'}</span>
                    </div>
                    <div className="text-[11.5px] text-ink/40 mt-1 font-mono">{d.reference} · Submitted {d.submitted_at?new Date(d.submitted_at).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):''}</div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button onClick={()=>reject(d)} className="btn-ghost btn-sm text-brand-red border-brand-red/20 hover:bg-brand-red-bg">Request data</button>
                    <button onClick={()=>approve(d)} disabled={approving===d.id} className="btn-primary btn-sm">
                      {approving===d.id?'Releasing...':'Approve & release'}
                    </button>
                  </div>
                </div>

                {isLowConf&&(
                  <div className="alert-red mb-4"><AlertTriangle size={13}/>Low confidence: key data fields missing. Analysis precision significantly degraded. Consider requesting more data.</div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-[10.5px] text-ink/40 uppercase tracking-wider font-medium mb-2">AI-generated estimate</div>
                    <div className="flex gap-4 mb-3">
                      {[['Low',est.low],['Mid',est.mid],['High',est.high]].map(([l,v])=>(
                        <div key={l as string}><div className="text-[10px] text-ink/40 mb-0.5">{l}</div><div className="text-[14px] font-medium font-mono">{fmtCurrency(v as number)}</div></div>
                      ))}
                    </div>
                    <div className="narr text-[11.5px] mb-3">{ai.executive_summary||'No summary generated.'}</div>
                    <div className="text-[10.5px] text-ink/40 uppercase tracking-wider font-medium mb-2">Assumptions log</div>
                    <div className="bg-surface-2 rounded-lg p-3 text-[11.5px] text-ink/60 leading-relaxed max-h-32 overflow-y-auto">
                      {(ai.assumptions_used||[]).map((a:string,i:number)=><div key={i}>• {a}</div>)}
                      {(!ai.assumptions_used||ai.assumptions_used.length===0)&&<span className="text-ink/30">No assumptions logged</span>}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10.5px] text-ink/40 uppercase tracking-wider font-medium mb-2">Manual override (logged)</div>
                    <div className="bg-surface-2 rounded-lg p-3 mb-3">
                      <div className="grid grid-cols-3 gap-2 mb-2">
                        {[['Low (£K)','low'],['Mid (£K)','mid'],['High (£K)','high']].map(([l,k])=>(
                          <div key={k}><label className="label">{l}</label><input className="input" value={(ov as any)[k]} onChange={e=>setOvr(d.id,k,e.target.value)} placeholder="—"/></div>
                        ))}
                      </div>
                      <div><label className="label">Override reason</label><input className="input" value={ov.reason} onChange={e=>setOvr(d.id,'reason',e.target.value)} placeholder="Why are you changing AI values?"/></div>
                    </div>
                    <div className="text-[10.5px] text-ink/40 uppercase tracking-wider font-medium mb-2">Operator notes <span className="text-ink/25 normal-case font-normal">(never shown to client)</span></div>
                    <textarea className="input" rows={4} style={{resize:'none'}} value={notes[d.id]||''} onChange={e=>setNote(d.id,e.target.value)} placeholder="Log your reasoning, caveats, relationship context, follow-up flags..."/>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </AppShell>
  )
}
