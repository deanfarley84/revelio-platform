'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { diagnosticsApi, reportsApi, fmtCurrency, fmtPct, confidenceColour } from '@/lib/api'
import { useParams, useRouter } from 'next/navigation'
import { Download, ArrowLeft } from 'lucide-react'

export default function ResultsDetailPage() {
  const { id } = useParams() as { id: string }
  const router = useRouter()
  const [diag, setDiag] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (!id) return
    diagnosticsApi.get(id).then(r => { setDiag(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [id])

  const handleDownload = async (type: 'pdf'|'csv') => {
    setGenerating(true)
    try {
      await reportsApi.generate(id, type)
      setTimeout(async () => {
        const exports = await reportsApi.list(id)
        const exp = exports.data.find((e:any) => e.export_type===type && !e.is_internal)
        if (exp) {
          const blob = await reportsApi.download(id, exp.id)
          const url = window.URL.createObjectURL(new Blob([blob.data]))
          const a = document.createElement('a'); a.href=url; a.download=`revelio-${diag?.reference}.${type}`; a.click()
          window.URL.revokeObjectURL(url)
        }
        setGenerating(false)
      }, 3000)
    } catch { alert('Export failed'); setGenerating(false) }
  }

  if (loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading...</div></AppShell>
  if (!diag) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Report not found or not yet released.</div></AppShell>

  const out = diag.output||{}
  const est = out.annual_leakage_estimate||{}
  const imp = out.revenue_impact_pct||{}
  const drivers = out.primary_drivers||[]
  const breakdown = out.financial_breakdown||[]
  const fixes = out.recommended_fix_priorities||{}
  const gaps = out.data_gaps||[]

  return (
    <AppShell>
      <div className="max-w-6xl">
        <button onClick={()=>router.push('/results')} className="flex items-center gap-1.5 text-[12px] text-ink/50 hover:text-ink mb-5 transition-colors">
          <ArrowLeft size={13}/> Back to results
        </button>

        <div className="flex items-start justify-between mb-5">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <h1 className="text-xl font-medium">{diag.company_name}</h1>
              <span className={`tier-${diag.tier}`}>{diag.tier?.toUpperCase()}</span>
              <span className="tag tag-green">Released</span>
            </div>
            <div className="text-[12px] text-ink/40 font-mono">{diag.reference} · {diag.vertical} · Released {diag.released_at?new Date(diag.released_at).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'—'}</div>
          </div>
          <div className="flex gap-2">
            <button onClick={()=>handleDownload('csv')} disabled={generating} className="btn-ghost btn-sm"><Download size={12}/>CSV</button>
            <button onClick={()=>handleDownload('pdf')} disabled={generating} className="btn-primary btn-sm"><Download size={12}/>{generating?'Generating...':'PDF Report'}</button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="rounded-lg p-5" style={{background:'#1A1830',color:'white'}}>
            <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1.5">Mid estimate · Annual revenue leakage</div>
            <div className="text-[34px] font-light text-white/95 leading-none">{fmtCurrency(est.mid)}</div>
            <div className="text-[11px] text-white/40 mt-1.5">{fmtPct(imp.mid)} of annual processing volume · Confidence: <span className="capitalize">{out.confidence_level}</span></div>
            <div className="flex gap-5 mt-3 pt-3 border-t border-white/10">
              {[['Conservative',est.low],['Base case',est.mid],['Upside',est.high]].map(([l,v])=>(
                <div key={l as string}><div className="text-[9.5px] text-white/35">{l}</div><div className="text-[14px] font-medium text-white/82 font-mono">{fmtCurrency(v as number)}</div></div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[13px] font-medium">Executive summary</div>
              <div className="flex items-center gap-1.5 bg-surface-2 border border-black/[0.07] rounded-full px-2.5 py-1 text-[10px] text-ink/50">Claude AI · Reviewed</div>
            </div>
            <div className="narr mb-3">{out.executive_summary||'Summary not available.'}</div>
            {gaps.slice(0,3).map((g:string,i:number)=>(
              <div key={i} className="flex items-start gap-2 text-[11.5px] text-ink/50 py-1 border-b border-black/[0.04] last:border-0">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0"/>
                {g}
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="card">
            <div className="text-[13px] font-medium mb-4">Financial breakdown</div>
            {drivers.map((d:any)=>(
              <div key={d.rank} className="py-2.5 border-b border-black/[0.05] last:border-0">
                <div className="flex justify-between mb-1"><span className="text-[12.5px] font-medium">{d.rank}. {d.driver}</span><span className="text-[12.5px] font-medium font-mono">{fmtCurrency(d.estimated_impact_low)}–{fmtCurrency(d.estimated_impact_high)}</span></div>
                <div className="text-[11px] text-ink/40 mb-1.5">{d.explanation||''}</div>
                <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden mb-1.5">
                  <div className="h-full rounded-full" style={{width:`${Math.max(8,100-((d.rank-1)*18))}%`,background:d.rank===1?'#E24B4A':d.rank===2?'#EF9F27':'#378ADD'}}/>
                </div>
                <div className="flex items-center gap-2 text-[10.5px] text-ink/40">
                  <span className={`font-medium capitalize ${confidenceColour(d.confidence)}`}>{d.confidence} confidence</span>
                  <span>·</span><span className="capitalize">{d.basis}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="text-[13px] font-medium mb-4">Recommended priorities</div>
            {[{key:'immediate',label:'Immediate (0–30 days)',cls:'text-brand-red',bgCls:'bg-brand-red-bg text-brand-red'},
              {key:'mid_term',label:'Medium-term (30–90 days)',cls:'text-brand-amber',bgCls:'bg-brand-amber-bg text-brand-amber'},
              {key:'structural',label:'Structural (90+ days)',cls:'text-brand-blue',bgCls:'bg-brand-blue-bg text-brand-blue'}]
              .map(({key,label,cls,bgCls})=>fixes[key]?.length>0&&(
                <div key={key} className="mb-4">
                  <div className={`text-[10px] font-bold uppercase tracking-wider mb-2 ${cls}`}>{label}</div>
                  {fixes[key].map((item:any,i:number)=>(
                    <div key={i} className="flex gap-2.5 py-1.5">
                      <div className={`w-[18px] h-[18px] rounded-full flex items-center justify-center text-[9.5px] font-bold flex-shrink-0 mt-0.5 ${bgCls}`}>{i+1}</div>
                      <div><div className="text-[12px]">{item.action}</div>{item.estimated_recovery&&<div className="text-[11px] text-ink/40 mt-0.5">Est. recovery: {item.estimated_recovery}</div>}</div>
                    </div>
                  ))}
                </div>
              ))}
          </div>
        </div>

        {out.assumptions_used?.length>0&&(
          <div className="card">
            <div className="text-[13px] font-medium mb-3">Assumptions used in this analysis</div>
            <div className="grid grid-cols-2 gap-x-8">
              {out.assumptions_used.map((a:string,i:number)=>(
                <div key={i} className="text-[11.5px] text-ink/50 py-1.5 border-b border-black/[0.04] last:border-0">{a}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}
