'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { adminApi, diagnosticsApi, fmtCurrency, confidenceColour } from '@/lib/api'
import { BrainCircuit, Edit3, CheckCircle } from 'lucide-react'

export default function AIReviewPage() {
  const [queue, setQueue] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [editedNarrative, setEditedNarrative] = useState('')
  const [editingNarrative, setEditingNarrative] = useState(false)
  const [overrides, setOverrides] = useState({ low: '', mid: '', high: '', reason: '', confidence: '' })
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.queue().then(r => { setQueue(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const selectDiag = (d: any) => {
    setSelected(d)
    const ai = d.ai_output || {}
    setEditedNarrative(ai.executive_summary || '')
    setOverrides({ low: '', mid: '', high: '', reason: '', confidence: ai.confidence_level || '' })
    setNotes(d.operator_notes || '')
    setEditingNarrative(false)
  }

  const approve = async () => {
    if (!selected) return
    setSaving(true)
    try {
      const ai = selected.ai_output || {}
      const hasOverride = overrides.mid && parseFloat(overrides.mid) !== (ai.annual_leakage_estimate?.mid || 0)
      // Patch narrative into ai_output if edited
      const payload: any = { operator_notes: notes }
      if (hasOverride) {
        payload.override_enabled = true
        payload.override_low = parseFloat(overrides.low || '0')
        payload.override_mid = parseFloat(overrides.mid || '0')
        payload.override_high = parseFloat(overrides.high || '0')
        payload.override_reason = overrides.reason
        payload.override_confidence = overrides.confidence || undefined
      }
      await diagnosticsApi.approve(selected.id, payload)
      setQueue(q => q.filter(x => x.id !== selected.id))
      setSelected(null)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Approval failed')
    }
    setSaving(false)
  }

  if (loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading...</div></AppShell>

  return (
    <AppShell>
      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="section-title">AI output review</div>
            <div className="section-sub">Review, annotate and override Claude-generated analysis before client release</div>
          </div>
        </div>

        {queue.length === 0 && !selected ? (
          <div className="card text-center py-14">
            <CheckCircle size={28} className="text-brand-green mx-auto mb-3" />
            <div className="text-[13px] font-medium mb-1">No outputs pending review</div>
            <div className="text-[12px] text-ink/40">All AI-generated diagnostics have been reviewed.</div>
          </div>
        ) : (
          <div className="grid gap-4" style={{ gridTemplateColumns: selected ? '260px 1fr' : '1fr' }}>
            {/* Queue list */}
            <div className="card">
              <div className="text-[11.5px] font-medium text-ink/50 uppercase tracking-wider mb-3">
                Pending review ({queue.length})
              </div>
              <div className="space-y-1">
                {queue.map((d: any) => {
                  const ai = d.ai_output || {}
                  const isLow = ai.confidence_level === 'low'
                  return (
                    <div key={d.id} onClick={() => selectDiag(d)}
                      className={`p-3 rounded-lg cursor-pointer border transition-all ${selected?.id === d.id ? 'border-brand-blue bg-brand-blue-bg' : 'border-transparent hover:bg-surface-2'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="text-[12.5px] font-medium truncate flex-1">{d.company_name}</div>
                        {isLow && <span className="tag tag-red text-[9.5px] ml-1">Low conf.</span>}
                      </div>
                      <div className="text-[10.5px] text-ink/40 font-mono">{d.reference}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span>
                        <span className={`text-[10.5px] font-medium ${confidenceColour(ai.confidence_level)}`}>{ai.confidence_level}</span>
                        <span className="text-[10.5px] text-ink/40 font-mono">{fmtCurrency(ai.annual_leakage_estimate?.mid)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Detail panel */}
            {selected && (() => {
              const ai = selected.ai_output || {}
              const est = ai.annual_leakage_estimate || {}
              const drivers = ai.primary_drivers || []
              const assumptions = ai.assumptions_used || []
              return (
                <div className="space-y-4">
                  {/* Header */}
                  <div className="card">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2.5 mb-1">
                          <div className="text-[14px] font-medium">{selected.company_name}</div>
                          <span className={`tier-${selected.tier}`}>{selected.tier?.toUpperCase()}</span>
                          <div className="flex items-center gap-1.5 bg-surface-2 border border-black/[0.07] rounded-full px-2.5 py-1 text-[10px] text-ink/50">
                            <BrainCircuit size={10} />Claude AI · {ai._meta?.model?.split('-').slice(0,2).join(' ') || 'Claude'}
                          </div>
                        </div>
                        <div className="text-[11.5px] text-ink/40 font-mono">{selected.reference}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => setSelected(null)} className="btn-ghost btn-sm">Close</button>
                        <button onClick={approve} disabled={saving} className="btn-primary btn-sm">
                          {saving ? 'Releasing...' : 'Approve & release →'}
                        </button>
                      </div>
                    </div>

                    {/* Leakage estimates */}
                    <div className="flex gap-4 p-3 bg-surface-2 rounded-lg mb-4">
                      {[['Low', est.low], ['Mid (base case)', est.mid], ['High', est.high]].map(([l, v]) => (
                        <div key={l as string}>
                          <div className="text-[10px] text-ink/40 mb-0.5">{l}</div>
                          <div className="text-[15px] font-medium font-mono">{fmtCurrency(v as number)}</div>
                        </div>
                      ))}
                      <div className="ml-auto">
                        <div className="text-[10px] text-ink/40 mb-0.5">Confidence</div>
                        <div className={`text-[15px] font-medium capitalize ${confidenceColour(ai.confidence_level)}`}>{ai.confidence_level}</div>
                      </div>
                    </div>

                    {/* Executive narrative */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-[11px] text-ink/40 font-medium uppercase tracking-wider">AI executive summary</div>
                        <button onClick={() => setEditingNarrative(!editingNarrative)} className="btn-ghost btn-xs">
                          <Edit3 size={10} />{editingNarrative ? 'Done' : 'Edit'}
                        </button>
                      </div>
                      {editingNarrative ? (
                        <textarea className="input" rows={5} style={{ resize: 'none' }} value={editedNarrative} onChange={e => setEditedNarrative(e.target.value)} />
                      ) : (
                        <div className="narr">{editedNarrative || ai.executive_summary}</div>
                      )}
                    </div>

                    {/* Primary drivers */}
                    {drivers.length > 0 && (
                      <div className="mb-4">
                        <div className="text-[11px] text-ink/40 font-medium uppercase tracking-wider mb-2">Primary drivers</div>
                        <div className="space-y-2">
                          {drivers.map((d: any) => (
                            <div key={d.rank} className="flex items-start gap-3 p-2.5 bg-surface-2 rounded-lg">
                              <div className="w-5 h-5 rounded-full bg-white border border-black/[0.1] flex items-center justify-center text-[9.5px] font-bold flex-shrink-0 mt-0.5">{d.rank}</div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between">
                                  <span className="text-[12px] font-medium">{d.driver}</span>
                                  <span className="text-[11.5px] font-mono text-ink/70">{fmtCurrency(d.estimated_impact_low)}–{fmtCurrency(d.estimated_impact_high)}</span>
                                </div>
                                <div className="text-[11px] text-ink/50 mt-0.5">{d.explanation || d.calculation_basis}</div>
                                <div className="flex gap-2 mt-1">
                                  <span className={`text-[10px] font-medium capitalize ${confidenceColour(d.confidence)}`}>{d.confidence}</span>
                                  <span className="text-[10px] text-ink/30">·</span>
                                  <span className="text-[10px] text-ink/40 capitalize">{d.basis}</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Override + Notes */}
                  <div className="card">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[11px] text-ink/40 font-medium uppercase tracking-wider mb-2">Manual value override</div>
                        <div className="bg-surface-2 rounded-lg p-3">
                          <div className="grid grid-cols-3 gap-2 mb-2">
                            {[['Low (£K)', 'low'], ['Mid (£K)', 'mid'], ['High (£K)', 'high']].map(([l, k]) => (
                              <div key={k}><label className="label">{l}</label>
                                <input className="input" value={(overrides as any)[k]}
                                  onChange={e => setOverrides(p => ({ ...p, [k]: e.target.value }))}
                                  placeholder={String(Math.round((est as any)[k === 'mid' ? 'mid' : k === 'low' ? 'low' : 'high'] / 1000))} />
                              </div>
                            ))}
                          </div>
                          <div className="mb-2"><label className="label">Override reason</label>
                            <input className="input" value={overrides.reason} onChange={e => setOverrides(p => ({ ...p, reason: e.target.value }))} placeholder="Why are you changing AI values?" />
                          </div>
                          <div><label className="label">Confidence override</label>
                            <select className="input" value={overrides.confidence} onChange={e => setOverrides(p => ({ ...p, confidence: e.target.value }))}>
                              <option value="">Keep AI value</option>
                              <option value="low">Low</option>
                              <option value="medium">Medium</option>
                              <option value="high">High</option>
                            </select>
                          </div>
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] text-ink/40 font-medium uppercase tracking-wider mb-2">Operator notes <span className="text-ink/25 normal-case font-normal">(never shown to client)</span></div>
                        <textarea className="input h-full" style={{ resize: 'none', minHeight: '160px' }} value={notes} onChange={e => setNotes(e.target.value)}
                          placeholder="Log your review reasoning, caveats, relationship context, follow-up triggers, or internal flags..." />
                      </div>
                    </div>
                  </div>

                  {/* Assumptions log */}
                  {assumptions.length > 0 && (
                    <div className="card">
                      <div className="text-[11px] text-ink/40 font-medium uppercase tracking-wider mb-2">AI assumption log</div>
                      <div className="grid grid-cols-2 gap-x-8">
                        {assumptions.map((a: string, i: number) => (
                          <div key={i} className="text-[11.5px] text-ink/60 py-1.5 border-b border-black/[0.04] last:border-0">• {a}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}
      </div>
    </AppShell>
  )
}
