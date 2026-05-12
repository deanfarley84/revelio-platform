'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { diagnosticsApi, reportsApi, fmtCurrency } from '@/lib/api'
import { Download, FileText, CheckCircle } from 'lucide-react'

export default function ReportsPage() {
  const [diagnostics, setDiagnostics] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState<string | null>(null)

  useEffect(() => {
    diagnosticsApi.list().then(r => {
      setDiagnostics(r.data.filter((d: any) => d.status === 'released'))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleDownload = async (diagId: string, ref: string, type: 'pdf' | 'csv') => {
    setGenerating(`${diagId}-${type}`)
    try {
      await reportsApi.generate(diagId, type, false)
      await new Promise(res => setTimeout(res, 3000)) // wait for generation
      const exportsRes = await reportsApi.list(diagId)
      const exp = exportsRes.data.find((e: any) => e.export_type === type && !e.is_internal)
      if (exp) {
        const blob = await reportsApi.download(diagId, exp.id)
        const url = window.URL.createObjectURL(new Blob([blob.data]))
        const a = document.createElement('a')
        a.href = url
        a.download = `vyre-${ref}.${type}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } else {
        alert('Report generation in progress — please try again in a moment.')
      }
    } catch {
      alert('Download failed. Please try again.')
    }
    setGenerating(null)
  }

  return (
    <AppShell>
      <div className="max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="section-title">Reports</div>
            <div className="section-sub">Approved diagnostic reports available for download</div>
          </div>
        </div>

        {loading ? (
          <div className="text-[13px] text-ink/40 py-12 text-center">Loading reports...</div>
        ) : diagnostics.length === 0 ? (
          <div className="card text-center py-14">
            <FileText size={28} className="text-ink/20 mx-auto mb-3" />
            <div className="text-[13px] font-medium text-ink/40 mb-1">No reports yet</div>
            <div className="text-[12px] text-ink/30">Reports appear here once your diagnostic has been approved and released.</div>
          </div>
        ) : (
          <div className="space-y-3">
            {diagnostics.map((d: any) => {
              const out = d.output || {}
              const est = out.annual_leakage_estimate || {}
              const isPdfGenerating = generating === `${d.id}-pdf`
              const isCsvGenerating = generating === `${d.id}-csv`
              return (
                <div key={d.id} className="card">
                  <div className="flex items-center justify-between">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-surface-2 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <FileText size={16} className="text-ink/40" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2.5 mb-0.5">
                          <div className="text-[13px] font-medium">{d.company_name} — {new Date(d.released_at || d.approved_at).toLocaleDateString('en-GB', { month:'long', year:'numeric' })} Diagnostic</div>
                          <span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span>
                          <span className="tag tag-green flex items-center gap-1"><CheckCircle size={9} />Released</span>
                        </div>
                        <div className="text-[11.5px] text-ink/40 font-mono mb-1">{d.reference}</div>
                        <div className="flex items-center gap-4 text-[11.5px] text-ink/50">
                          <span>Leakage est. (mid): <strong className="text-ink/80 font-mono">{fmtCurrency(est.mid)}</strong></span>
                          <span>Released: {d.released_at ? new Date(d.released_at).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' }) : '—'}</span>
                          <span className={`font-medium capitalize ${out.confidence_level === 'high' ? 'text-brand-green' : out.confidence_level === 'medium' ? 'text-brand-amber' : 'text-brand-red'}`}>
                            {out.confidence_level} confidence
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleDownload(d.id, d.reference, 'csv')}
                        disabled={!!generating}
                        className="btn-ghost btn-sm"
                      >
                        <Download size={12} />
                        {isCsvGenerating ? 'Generating...' : 'CSV'}
                      </button>
                      <button
                        onClick={() => handleDownload(d.id, d.reference, 'pdf')}
                        disabled={!!generating}
                        className="btn-primary btn-sm"
                      >
                        <Download size={12} />
                        {isPdfGenerating ? 'Generating...' : 'PDF Report'}
                      </button>
                    </div>
                  </div>

                  {/* Mini preview of top drivers */}
                  {out.primary_drivers?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-black/[0.05] flex items-center gap-3 flex-wrap">
                      <span className="text-[10.5px] text-ink/40 font-medium">Top drivers:</span>
                      {out.primary_drivers.slice(0, 3).map((drv: any, i: number) => (
                        <span key={i} className="tag tag-gray text-[10.5px]">{drv.driver} · {fmtCurrency(drv.estimated_impact_mid || drv.estimated_impact_low)}</span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Info box */}
        <div className="card mt-5" style={{ background:'#F0EEE9', border:'none' }}>
          <div className="text-[12px] font-medium mb-1.5">About your reports</div>
          <div className="text-[11.5px] text-ink/60 leading-relaxed">
            PDF reports include the executive summary, financial breakdown, leakage estimates, and recommended fix priorities — formatted for CFO or board presentation.
            CSV exports contain the category-level financial breakdown for use in your own analysis tools.
            All reports are generated from approved, operator-reviewed data.
          </div>
        </div>
      </div>
    </AppShell>
  )
}
