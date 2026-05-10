'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { adminApi, fmtCurrency } from '@/lib/api'
import Link from 'next/link'

export default function AdminClientsPage() {
  const [clients, setClients] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState('')

  useEffect(() => {
    adminApi.clients().then(r => { setClients(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const filtered = clients.filter(c => {
    const matchSearch = !search || c.name?.toLowerCase().includes(search.toLowerCase()) || c.vertical?.toLowerCase().includes(search.toLowerCase()) || c.website?.toLowerCase().includes(search.toLowerCase())
    const matchTier = !tierFilter || c.tier === tierFilter
    return matchSearch && matchTier
  })

  const stageColour = (s: string) => {
    if (!s) return 'tag-gray'
    if (['closed_won', 'report_delivered'].includes(s)) return 'tag-green'
    if (['upsell_target', 'follow_up', 'engaged'].includes(s)) return 'tag-blue'
    if (['diagnostic_in_progress'].includes(s)) return 'tag-amber'
    return 'tag-gray'
  }

  return (
    <AppShell>
      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="section-title">All clients</div>
            <div className="section-sub">{clients.length} organisations · {filtered.length} shown</div>
          </div>
          <div className="flex gap-2">
            <select className="input w-40" value={tierFilter} onChange={e => setTierFilter(e.target.value)}>
              <option value="">All tiers</option>
              <option value="lite">Lite</option>
              <option value="core">Core</option>
              <option value="enterprise">Enterprise</option>
            </select>
            <input className="input w-52" placeholder="Search name, vertical, website..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
        </div>

        <div className="card">
          {loading ? (
            <p className="text-[12px] text-ink/40 py-8 text-center">Loading clients...</p>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{width:'22%'}}>Organisation</th>
                  <th style={{width:'8%'}}>Tier</th>
                  <th style={{width:'10%'}}>Vertical</th>
                  <th style={{width:'14%'}}>Latest diagnostic</th>
                  <th style={{width:'12%'}}>Leakage (mid)</th>
                  <th style={{width:'10%'}}>Confidence</th>
                  <th style={{width:'12%'}}>Stage</th>
                  <th style={{width:'12%'}}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c: any) => {
                  const d = c.latest_diagnostic
                  const intel = c.intel
                  return (
                    <tr key={c.id}>
                      <td>
                        <div className="font-medium text-[12.5px] flex items-center gap-1.5">
                          <span>{c.name}</span>
                          {c.is_demo && <span className="tag tag-amber text-[9.5px]">DEMO</span>}
                        </div>
                        <div className="text-[10.5px] text-ink/40">{c.website || '—'}</div>
                      </td>
                      <td><span className={`tier-${c.tier}`}>{c.tier?.toUpperCase()}</span></td>
                      <td className="text-ink/60 capitalize text-[11.5px]">{c.vertical || '—'}</td>
                      <td className="font-mono text-[11px] text-ink/50">{d?.reference || '—'}</td>
                      <td className="font-mono text-[12px]">{d?.leakage_mid ? fmtCurrency(d.leakage_mid) : '—'}</td>
                      <td>
                        {d?.confidence_level ? (
                          <span className={`text-[11.5px] font-medium capitalize ${d.confidence_level === 'high' ? 'text-brand-green' : d.confidence_level === 'medium' ? 'text-brand-amber' : 'text-brand-red'}`}>
                            {d.confidence_level}
                          </span>
                        ) : '—'}
                      </td>
                      <td>
                        {intel?.opportunity_stage ? (
                          <span className={`tag ${stageColour(intel.opportunity_stage)} text-[10px] capitalize`}>
                            {intel.opportunity_stage.replace(/_/g, ' ')}
                          </span>
                        ) : <span className="text-ink/30 text-[11px]">—</span>}
                      </td>
                      <td>
                        <div className="flex gap-1.5">
                          <Link href="/admin/intel" className="btn-ghost btn-xs">Intel</Link>
                          {d?.status === 'pending_review' && (
                            <Link href="/admin/queue" className="btn-ghost btn-xs text-brand-amber border-brand-amber/20">Review</Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {filtered.length === 0 && (
                  <tr><td colSpan={8} className="text-center text-ink/40 py-8">No clients found</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Summary stats */}
        {!loading && clients.length > 0 && (
          <div className="grid grid-cols-4 gap-3 mt-4">
            {[
              { label: 'Lite tier', count: clients.filter(c => c.tier === 'lite').length },
              { label: 'Core tier', count: clients.filter(c => c.tier === 'core').length },
              { label: 'Enterprise tier', count: clients.filter(c => c.tier === 'enterprise').length },
              { label: 'With intel records', count: clients.filter(c => c.intel).length },
            ].map(({ label, count }) => (
              <div key={label} className="card py-3">
                <div className="text-[10.5px] text-ink/40 font-medium uppercase tracking-wider mb-1">{label}</div>
                <div className="text-xl font-medium">{count}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}
