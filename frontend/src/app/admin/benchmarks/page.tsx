'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { benchmarksApi } from '@/lib/api'
import { CheckCircle } from 'lucide-react'

export default function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<any[]>([])
  const [edits, setEdits] = useState<Record<string,any>>({})
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)

  useEffect(()=>{benchmarksApi.list().then(r=>{setBenchmarks(r.data);setLoading(false)}).catch(()=>setLoading(false))},[])

  const setEdit=(id:string,key:string,value:string)=>setEdits(p=>({...p,[id]:{...(p[id]||{}),id,[key]:value}}))

  const saveAll=async()=>{
    const updates=Object.values(edits).filter((e:any)=>e.id).map((e:any)=>({
      id:e.id,
      value_default:e.value_default!=null?parseFloat(e.value_default):undefined,
      value_low:e.value_low!=null?parseFloat(e.value_low):undefined,
      value_high:e.value_high!=null?parseFloat(e.value_high):undefined,
    }))
    await benchmarksApi.bulkUpdate(updates)
    setEdits({});setSaved(true);setTimeout(()=>setSaved(false),3000)
    benchmarksApi.list().then(r=>setBenchmarks(r.data))
  }

  const grouped=benchmarks.reduce((acc:any,b:any)=>{if(!acc[b.category])acc[b.category]=[];acc[b.category].push(b);return acc},{})
  const catLabel:Record<string,string>={auth_rate:'Authorisation rates by vertical',leakage:'Leakage assumptions',chargeback:'Chargeback assumptions',confidence:'Confidence thresholds'}

  if(loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading...</div></AppShell>

  return (
    <AppShell>
      <div className="max-w-5xl">
        <div className="flex items-center justify-between mb-5">
          <div><div className="section-title">Benchmark configuration</div><div className="section-sub">Injected live into Claude AI analysis. Changes apply to all future diagnostics immediately.</div></div>
          <div className="flex items-center gap-3">
            {saved&&<div className="flex items-center gap-1.5 text-[12px] text-brand-green"><CheckCircle size={13}/>Saved</div>}
            <button onClick={saveAll} disabled={Object.keys(edits).length===0} className="btn-primary">Save all changes</button>
          </div>
        </div>
        <div className="space-y-4">
          {Object.entries(grouped).map(([cat,rows]:any)=>(
            <div key={cat} className="card">
              <div className="text-[13px] font-medium mb-1">{catLabel[cat]||cat}</div>
              <div className="flex gap-2 text-[10px] text-ink/40 font-medium uppercase tracking-wider mt-3 mb-1 px-1">
                <span className="flex-1">Benchmark</span><span className="w-28 text-center">Range</span><span className="w-24 text-center">Default</span><span className="w-24 text-center">Low</span><span className="w-24 text-center">High</span>
              </div>
              {rows.map((b:any)=>{
                const e=edits[b.id]||{}
                return(
                  <div key={b.id} className="flex items-center gap-2 py-2.5 border-b border-black/[0.05] last:border-0 px-1">
                    <div className="flex-1"><div className="text-[12.5px]">{b.label}</div>{b.vertical!=='all'&&<div className="text-[10.5px] text-ink/40">{b.vertical}</div>}</div>
                    <div className="w-28 text-center text-[11px] font-mono text-ink/40">{b.value_low}–{b.value_high}{b.unit==='percent'?'%':''}</div>
                    {['value_default','value_low','value_high'].map(k=>(
                      <input key={k} className="w-24 border border-black/[0.13] rounded px-2 py-1.5 text-[12px] text-right font-mono outline-none focus:border-brand-blue bg-white"
                        value={(e[k]??b[k])??''} onChange={v=>setEdit(b.id,k,v.target.value)}/>
                    ))}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  )
}
