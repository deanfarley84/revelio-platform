'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import Link from 'next/link'
import { diagnosticsApi, fmtCurrency, fmtPct, statusColour, confidenceColour } from '@/lib/api'
import { ArrowUpRight, TrendingDown } from 'lucide-react'

export default function DashboardPage() {
  const [diagnostics, setDiagnostics] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    diagnosticsApi.list().then(r => { setDiagnostics(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const latest = diagnostics[0]
  const output = latest?.output || {}
  const estimate = output.annual_leakage_estimate || {}
  const drivers = output.primary_drivers || []

  return (
    <AppShell>
      <div className="max-w-6xl">
        {/* KPIs */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="kpi-card">
            <div className="kpi-label">Annual leakage (mid)</div>
            <div className="kpi-value">{fmtCurrency(estimate.mid)}</div>
            <div className="flex items-center gap-1 mt-1.5 text-[11px] text-brand-red">
              <TrendingDown size={10} />
              {fmtPct(output.revenue_impact_pct?.mid)} of revenue
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Auth rate</div>
            <div className="kpi-value">{latest?.auth_rate ? fmtPct(latest.auth_rate) : '—'}</div>
            <div className="text-[11px] text-ink/40 mt-1.5">Benchmark: 90–95%</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Chargeback rate</div>
            <div className="kpi-value">{latest?.chargeback_rate ? fmtPct(latest.chargeback_rate) : '—'}</div>
            <div className="text-[11px] text-ink/40 mt-1.5">Threshold: 0.6%</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Service tier</div>
            <div className="mt-2">
              <span className={`tier-${latest?.tier || 'lite'}`}>{(latest?.tier || 'LITE').toUpperCase()}</span>
            </div>
            <Link href="/submit" className="text-[11px] text-brand-blue mt-2 block">Upgrade →</Link>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Leakage estimate */}
          <div>
            <div className="rounded-lg p-5 mb-4" style={{ background: '#1A1830', color: 'white' }}>
              <div className="text-[10px] text-white/40 uppercase tracking-widest mb-1.5">Mid estimate · Annual revenue leakage</div>
              <div className="text-[32px] font-light text-white/95 leading-none">{fmtCurrency(estimate.mid)}</div>
              <div className="text-[11px] text-white/40 mt-1">Based on {latest?.company_name || 'your'} annual processing volume</div>
              <div className="flex gap-5 mt-3 pt-3 border-t border-white/10">
                {[['Conservative', estimate.low], ['Base case', estimate.mid], ['Upside', estimate.high]].map(([l, v]) => (
                  <div key={l as string}><div className="text-[9.5px] text-white/35">{l}</div><div className="text-[14px] font-medium text-white/82 font-mono">{fmtCurrency(v as number)}</div></div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <div className="text-[13px] font-medium">Primary leakage drivers</div>
                {latest && <span className="tag tag-green">Approved</span>}
              </div>
              {drivers.length === 0 && <p className="text-[12px] text-ink/40">No analysis yet. <Link href="/submit" className="text-brand-blue">Submit a diagnostic →</Link></p>}
              {drivers.map((d: any) => (
                <div key={d.rank} className="py-2.5 border-b border-black/[0.05] last:border-0">
                  <div className="flex justify-between mb-1">
                    <span className="text-[12.5px] font-medium">{d.rank}. {d.driver}</span>
                    <span className="text-[12.5px] font-medium font-mono">{fmtCurrency(d.estimated_impact_low)}–{fmtCurrency(d.estimated_impact_high)}</span>
                  </div>
                  <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.min(100, (d.rank === 1 ? 72 : d.rank === 2 ? 44 : d.rank === 3 ? 33 : 20))}%`, background: d.rank === 1 ? '#E24B4A' : d.rank === 2 ? '#EF9F27' : '#378ADD' }} />
                  </div>
                  <div className="text-[11px] text-ink/40 mt-1">{d.explanation || d.basis}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-4">
            {/* Executive summary */}
            {output.executive_summary && (
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-[13px] font-medium">Executive summary</div>
                  <div className="flex items-center gap-1.5 bg-surface-2 border border-black/[0.07] rounded-full px-2.5 py-1 text-[10px] text-ink/50">
                    AI · Operator reviewed
                  </div>
                </div>
                <div className="narr">{output.executive_summary}</div>
              </div>
            )}

            {/* Diagnostic status */}
            {latest && (
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-[13px] font-medium">Diagnostic status</div>
                  <span className={`tag ${latest.status === 'released' ? 'tag-green' : latest.status === 'pending_review' ? 'tag-amber' : 'tag-gray'}`}>{latest.status?.replace('_', ' ')}</span>
                </div>
                <div className="space-y-2 text-[12px]">
                  {[
                    ['Data validated', latest.submitted_at],
                    ['AI analysis complete', latest.submitted_at],
                    ['Operator review', latest.approved_at],
                    ['Report released', latest.released_at],
                  ].map(([label, date]) => (
                    <div key={label as string} className="flex items-center gap-2">
                      <span className={`dot ${date ? 'dot-g' : 'dot-gy'}`} />
                      <span className="flex-1 text-ink/70">{label}</span>
                      {date && <span className="text-[10.5px] text-ink/40">{new Date(date as string).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* CTA */}
            <div className="card border-dashed border-2 border-black/[0.1] flex items-center justify-between">
              <div>
                <div className="text-[13px] font-medium mb-1">Run a new diagnostic</div>
                <div className="text-[12px] text-ink/50">Upload files or enter data manually</div>
              </div>
              <Link href="/submit" className="btn-primary btn-sm flex items-center gap-1">Start <ArrowUpRight size={12} /></Link>
            </div>
          </div>
        </div>

        {/* Diagnostics table */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[13px] font-medium">Diagnostic history</div>
            <Link href="/submit" className="btn-ghost btn-sm">+ New diagnostic</Link>
          </div>
          {loading ? <p className="text-[12px] text-ink/40 py-4 text-center">Loading...</p> : (
            <table className="tbl">
              <thead><tr><th>Reference</th><th>Tier</th><th>Submitted</th><th>Status</th><th>Est. leakage (mid)</th><th>Confidence</th><th></th></tr></thead>
              <tbody>
                {diagnostics.map((d: any) => {
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
                      <td><span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span></td>
                      <td className="text-ink/50">{d.submitted_at ? new Date(d.submitted_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}</td>
                      <td><span className={`dot ${statusColour(d.status)}`} />{d.status?.replace(/_/g, ' ')}</td>
                      <td className="font-mono">{fmtCurrency(est.mid)}</td>
                      <td className={`font-medium ${confidenceColour(o.confidence_level)}`}>{o.confidence_level || '—'}</td>
                      <td><Link href={`/results/${d.id}`} className="btn-ghost btn-xs">View →</Link></td>
                    </tr>
                  )
                })}
                {diagnostics.length === 0 && (
                  <tr><td colSpan={7} className="text-center text-ink/40 py-6">No diagnostics yet. <Link href="/submit" className="text-brand-blue">Submit your first →</Link></td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  )
}
