'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { diagnosticsApi, fmtCurrency, statusColour, confidenceColour } from '@/lib/api'
import Link from 'next/link'

export default function ResultsPage() {
  const [diagnostics, setDiagnostics] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    diagnosticsApi.list().then(r => { setDiagnostics(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  return (
    <AppShell>
      <div className="max-w-5xl">
        <div className="flex items-center justify-between mb-5">
          <div><div className="section-title">My results</div><div className="section-sub">All approved and released diagnostics</div></div>
          <Link href="/submit" className="btn-primary btn-sm">+ New diagnostic</Link>
        </div>
        <div className="card">
          {loading ? <p className="text-[12px] text-ink/40 py-8 text-center">Loading...</p> : (
            <table className="tbl">
              <thead><tr><th>Reference</th><th>Submitted</th><th>Tier</th><th>Status</th><th>Leakage (mid)</th><th>Confidence</th><th>Action</th></tr></thead>
              <tbody>
                {diagnostics.map((d:any) => {
                  const o = d.output || {}
                  const est = o.annual_leakage_estimate || {}
                  return (
                    <tr key={d.id}>
                      <td className="font-mono text-[11.5px]">
                        <span className="inline-flex items-center gap-1.5">
                          {d.reference}
                          {d.is_demo && <span className="tag tag-amber text-[9.5px]">DEMO</span>}
                        </span>
                      </td>
                      <td className="text-ink/50">{d.submitted_at ? new Date(d.submitted_at).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}) : '—'}</td>
                      <td><span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span></td>
                      <td><span className={`dot ${statusColour(d.status)}`}/>{d.status?.replace(/_/g,' ')}</td>
                      <td className="font-mono">{fmtCurrency(est.mid)}</td>
                      <td className={`font-medium ${confidenceColour(o.confidence_level)}`}>{o.confidence_level||'—'}</td>
                      <td><Link href={`/results/${d.id}`} className="btn-ghost btn-xs">View →</Link></td>
                    </tr>
                  )
                })}
                {diagnostics.length===0 && (
                  <tr><td colSpan={7} className="text-center text-ink/40 py-8">No results yet. <Link href="/submit" className="text-brand-blue">Submit your first diagnostic →</Link></td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  )
}
