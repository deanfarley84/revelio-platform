'use client'
import React, { useEffect, useMemo, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { diagnosticsApi, fmtCurrency, reportsApi } from '@/lib/api'
import { Calculator, FileText, Plus, Trash2, Copy, Check, X, Info, TrendingUp, Download, Loader2 } from 'lucide-react'

type Mode = 'diagnostic' | 'manual'

type Driver = {
  id: string
  category: string
  estimatedLoss: number       // annual £
  recoveryRate: number        // 0–100 (% of loss recoverable)
  implementationCost: number  // one-off £
  confidence?: string
}

const DEFAULT_DRIVERS: Driver[] = [
  { id: 'd1', category: 'Authorisation loss',          estimatedLoss: 0, recoveryRate: 60, implementationCost: 0 },
  { id: 'd2', category: 'Cross-border performance',    estimatedLoss: 0, recoveryRate: 40, implementationCost: 0 },
  { id: 'd3', category: 'FX leakage',                  estimatedLoss: 0, recoveryRate: 70, implementationCost: 0 },
  { id: 'd4', category: 'Retry logic',                 estimatedLoss: 0, recoveryRate: 80, implementationCost: 0 },
]

// Mid-market UK retailer scenario, used when the dashboard has no released
// diagnostics yet so the calculator is never shown empty. Implementation
// cost defaults to zero across the board; payments leakage fixes are
// overwhelmingly configuration changes or vendor conversations rather
// than things the merchant has to "buy".
const DEMO_DRIVERS: Driver[] = [
  { id: 'demo1', category: 'Authorisation loss',       estimatedLoss: 480000, recoveryRate: 60, implementationCost: 0 },
  { id: 'demo2', category: 'Cross-border performance', estimatedLoss: 180000, recoveryRate: 40, implementationCost: 0 },
  { id: 'demo3', category: 'FX leakage',               estimatedLoss: 220000, recoveryRate: 70, implementationCost: 0 },
  { id: 'demo4', category: 'Retry logic',              estimatedLoss: 95000,  recoveryRate: 80, implementationCost: 0 },
]
const DEMO_COMPANY = 'Acme Retail (example)'

// Plain-English explainers and typical implementation cost ranges,
// surfaced as tooltips and per-row hints so merchants understand what
// each driver represents and what to budget. Categories are matched
// fuzzily so diagnostic-derived names that vary slightly still resolve.
const DRIVER_META: Record<string, { explainer: string; costRange: [number, number] }> = {
  'authorisation loss': {
    explainer: 'Approved transactions you are not capturing because the issuer declined.',
    costRange: [15000, 60000],
  },
  'cross-border performance': {
    explainer: 'Lost approvals on international transactions due to acquirer setup or routing.',
    costRange: [10000, 40000],
  },
  'fx leakage': {
    explainer: 'Margin lost to FX spread or settlement currency mismatch.',
    costRange: [5000, 25000],
  },
  'retry logic': {
    explainer: 'Soft declines that could be recovered with smarter retry timing or network tokens.',
    costRange: [8000, 30000],
  },
  'routing inefficiency': {
    explainer: 'Performance loss from single-PSP dependency or absence of failover.',
    costRange: [20000, 80000],
  },
  'chargeback admin': {
    explainer: 'Operational overhead and revenue loss from disputes and refunds.',
    costRange: [10000, 50000],
  },
  'payment method gaps': {
    explainer: 'Missed conversion from absent local payment methods in key markets.',
    costRange: [15000, 60000],
  },
}

function lookupDriverMeta(category: string) {
  const k = (category || '').toLowerCase()
  return Object.entries(DRIVER_META).find(([key]) => k.includes(key.split(' ')[0]))?.[1]
}

// Per-driver realistic recovery ceilings. Stops sales conversations
// with sliders dragged to 100% that buyers will dismiss.
const RECOVERY_CEILING: Record<string, number> = {
  'auth': 80,
  'cross': 60,
  'fx': 90,
  'retry': 90,
  'routing': 70,
  'chargeback': 65,
  'payment method': 55,
}

function ceilingFor(category: string): number {
  const c = (category || '').toLowerCase()
  for (const [key, val] of Object.entries(RECOVERY_CEILING)) {
    if (c.includes(key)) return val
  }
  return 95
}

export default function RoiPage() {
  const [mode, setMode] = useState<Mode>('diagnostic')
  const [diagnostics, setDiagnostics] = useState<any[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [drivers, setDrivers] = useState<Driver[]>(DEFAULT_DRIVERS)
  const [timeframeMonths, setTimeframeMonths] = useState<number>(12)
  const [companyName, setCompanyName] = useState<string>('')
  const [copied, setCopied] = useState(false)
  const [demoActive, setDemoActive] = useState(false)
  const [demoBannerDismissed, setDemoBannerDismissed] = useState(false)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)

  // Load released diagnostics for the dropdown
  useEffect(() => {
    diagnosticsApi.list()
      .then(r => {
        const released = (r.data || []).filter((d: any) =>
          ['released', 'approved'].includes(d.status) && d.output
        )
        setDiagnostics(released)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // Demo mode: enter once when the dashboard has no released diagnostics
  // so the calculator never lands empty for first-time visitors.
  useEffect(() => {
    if (loading || demoActive) return
    if (mode === 'diagnostic' && diagnostics.length === 0 && !selectedId) {
      setDrivers(DEMO_DRIVERS)
      setCompanyName(DEMO_COMPANY)
      setTimeframeMonths(12)
      setDemoActive(true)
    }
  }, [loading, mode, diagnostics, selectedId, demoActive])

  // Exit demo mode the moment the user picks a real diagnostic or switches
  // to manual. Diagnostic hydration is handled by the next effect; here we
  // only need to wipe demo data when going to manual.
  useEffect(() => {
    if (!demoActive) return
    if (selectedId) {
      setDemoActive(false)
      return
    }
    if (mode === 'manual') {
      setDrivers(DEFAULT_DRIVERS)
      setCompanyName('')
      setDemoActive(false)
    }
  }, [demoActive, selectedId, mode])

  // When a diagnostic is selected, hydrate drivers from financial_breakdown
  useEffect(() => {
    if (mode !== 'diagnostic' || !selectedId) return
    const d = diagnostics.find(x => x.id === selectedId)
    if (!d) return
    setCompanyName(d.organisation?.name || d.reference || '')
    const breakdown = d.output?.financial_breakdown || []
    if (breakdown.length === 0) {
      setDrivers(DEFAULT_DRIVERS)
      return
    }
    const next: Driver[] = breakdown.map((b: any, i: number) => ({
      id: `b${i}`,
      category: b.category || `Driver ${i + 1}`,
      estimatedLoss: Number(b.estimated_loss) || 0,
      recoveryRate: Math.min(defaultRecoveryRate(b.category), ceilingFor(b.category)),
      implementationCost: 0,
      confidence: b.confidence,
    }))
    setDrivers(next)
  }, [mode, selectedId, diagnostics])

  // Computed totals. Mid case is the slider-driven number; low and high
  // bracket it by scaling each driver's recovery rate by 0.6 / 1.2 (high
  // capped at the per-driver ceiling). Cost stays constant across cases.
  const totals = useMemo(() => {
    const totalCost = drivers.reduce((sum, d) => sum + d.implementationCost, 0)

    const annualForFactor = (factor: number) =>
      drivers.reduce((sum, d) => {
        const rate = factor === 1
          ? d.recoveryRate
          : Math.min(d.recoveryRate * factor, ceilingFor(d.category))
        return sum + (d.estimatedLoss * rate / 100)
      }, 0)

    const buildCase = (factor: number) => {
      const annualRecoverable = annualForFactor(factor)
      const periodRecoverable = annualRecoverable * (timeframeMonths / 12)
      const monthlyRecoverable = annualRecoverable / 12
      return {
        annualRecoverable,
        periodRecoverable,
        roiMultiple: totalCost > 0 ? periodRecoverable / totalCost : null,
        paybackWeeks: monthlyRecoverable > 0 ? (totalCost / monthlyRecoverable) * (52 / 12) : null,
      }
    }

    const low = buildCase(0.6)
    const mid = buildCase(1)
    const high = buildCase(1.2)

    return {
      annualRecoverable: mid.annualRecoverable,
      totalCost,
      periodRecoverable: mid.periodRecoverable,
      netGain: mid.periodRecoverable - totalCost,
      roiMultiple: mid.roiMultiple,
      paybackWeeks: mid.paybackWeeks,
      low,
      high,
    }
  }, [drivers, timeframeMonths])

  // Driver mutations
  const updateDriver = (id: string, patch: Partial<Driver>) => {
    setDrivers(prev => prev.map(d => d.id === id ? { ...d, ...patch } : d))
  }
  const addDriver = () => {
    setDrivers(prev => [...prev, {
      id: `m${Date.now()}`,
      category: 'New driver',
      estimatedLoss: 0,
      recoveryRate: 50,
      implementationCost: 0,
    }])
  }
  const removeDriver = (id: string) => {
    setDrivers(prev => prev.filter(d => d.id !== id))
  }
  const resetToExample = () => {
    setDrivers(DEMO_DRIVERS)
    setCompanyName(DEMO_COMPANY)
    setTimeframeMonths(12)
  }

  const copySummary = async () => {
    const lines = [
      `Revelio ROI Summary${companyName ? ` — ${companyName}` : ''}`,
      `Timeframe: ${timeframeMonths} months`,
      ``,
      `Recoverable revenue (period): ${fmtCurrency(totals.periodRecoverable)}`,
      `Implementation cost (one-off): ${fmtCurrency(totals.totalCost)}`,
      `Net gain (period): ${fmtCurrency(totals.netGain)}`,
      `ROI multiple: ${totals.roiMultiple != null ? totals.roiMultiple.toFixed(1) + 'x' : 'n/a'}`,
      `Payback: ${totals.paybackWeeks != null ? totals.paybackWeeks.toFixed(1) + ' weeks' : 'n/a'}`,
      ``,
      `Drivers:`,
      ...drivers.map(d =>
        `  • ${d.category}: loss ${fmtCurrency(d.estimatedLoss)} × ${d.recoveryRate}% recovery − cost ${fmtCurrency(d.implementationCost)} = ${fmtCurrency(d.estimatedLoss * d.recoveryRate / 100 - d.implementationCost)} net annual`
      ),
    ].join('\n')
    try {
      await navigator.clipboard.writeText(lines)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch { /* noop */ }
  }

  const downloadPdf = async () => {
    if (pdfBusy) return
    setPdfBusy(true)
    setPdfError(null)
    try {
      const res = await reportsApi.roiPdf({
        companyName: companyName || 'Scenario',
        timeframeMonths,
        drivers,
        totals: {
          periodRecoverable: totals.periodRecoverable,
          totalCost: totals.totalCost,
          roiMultiple: totals.roiMultiple,
          paybackWeeks: totals.paybackWeeks,
        },
        scenarioRange: {
          lowRecoverable: totals.low.periodRecoverable,
          highRecoverable: totals.high.periodRecoverable,
          lowRoi: totals.low.roiMultiple,
          highRoi: totals.high.roiMultiple,
        },
      })
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const slug = (companyName || 'scenario').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'scenario'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `revelio-roi-${slug}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      setPdfError('Could not generate PDF, try again or use Copy summary.')
    } finally {
      setPdfBusy(false)
    }
  }

  return (
    <AppShell>
      <div className="max-w-6xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="section-title flex items-center gap-2">
              <Calculator size={16} className="text-ink/70" />
              ROI calculator
            </div>
            <div className="section-sub">Model the commercial return on fixing identified leakage</div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={copySummary} disabled={pdfBusy} className="btn-ghost btn-sm">
              {copied ? <><Check size={13}/> Copied</> : <><Copy size={13}/> Copy summary</>}
            </button>
            <button onClick={downloadPdf} disabled={pdfBusy} className="btn-ghost btn-sm">
              {pdfBusy ? <><Loader2 size={13} className="animate-spin"/> Generating</> : <><Download size={13}/> Download PDF</>}
            </button>
          </div>
        </div>
        {pdfError && (
          <div className="text-[12px] text-brand-red mb-3 -mt-2">{pdfError}</div>
        )}

        {/* Mode toggle */}
        <div className="card mb-4">
          {demoActive && !demoBannerDismissed && (
            <div className="bg-surface-2 rounded-md px-3 py-2 mb-3 flex items-start justify-between text-[12px] text-ink/70 gap-3">
              <span>Showing example data. The cost to recover is £0, most fixes are configuration changes or conversations with providers. Add costs only if orchestration or advisory apply.</span>
              <button
                onClick={() => setDemoBannerDismissed(true)}
                className="text-ink/40 hover:text-ink/70 mt-0.5 shrink-0"
                aria-label="Dismiss example banner"
              >
                <X size={12}/>
              </button>
            </div>
          )}
          <div className="flex items-center justify-between mb-3 gap-3">
            <div className="flex items-center gap-1 p-1 bg-surface-2 rounded-md w-fit">
              <button
                onClick={() => setMode('diagnostic')}
                className={`px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${mode === 'diagnostic' ? 'bg-white text-ink shadow-sm' : 'text-ink/55'}`}
              >
                <FileText size={12} className="inline mr-1.5" />
                From diagnostic
              </button>
              <button
                onClick={() => setMode('manual')}
                className={`px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${mode === 'manual' ? 'bg-white text-ink shadow-sm' : 'text-ink/55'}`}
              >
                <Plus size={12} className="inline mr-1.5" />
                Manual inputs
              </button>
            </div>
            {demoActive && (
              <button onClick={resetToExample} className="btn-ghost btn-xs">
                Reset to example
              </button>
            )}
          </div>

          {mode === 'diagnostic' && (
            <div className="form-grid-2">
              <div>
                <label className="label">Released diagnostic</label>
                <select
                  className="select"
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                  disabled={loading}
                >
                  <option value="">{loading ? 'Loading…' : diagnostics.length === 0 ? 'No released diagnostics yet' : 'Select a diagnostic'}</option>
                  {diagnostics.map(d => (
                    <option key={d.id} value={d.id}>
                      {d.reference} — {d.organisation?.name || d.tier?.toUpperCase()} — mid {fmtCurrency(d.output?.annual_leakage_estimate?.mid)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Timeframe</label>
                <select className="select" value={timeframeMonths} onChange={e => setTimeframeMonths(Number(e.target.value))}>
                  <option value={12}>12 months</option>
                  <option value={24}>24 months</option>
                  <option value={36}>36 months</option>
                </select>
              </div>
            </div>
          )}

          {mode === 'manual' && (
            <div className="form-grid-2">
              <div>
                <label className="label">Company / scenario name</label>
                <input className="input" value={companyName} onChange={e => setCompanyName(e.target.value)} placeholder="e.g. Acme Retail — Q4 model" />
              </div>
              <div>
                <label className="label">Timeframe</label>
                <select className="select" value={timeframeMonths} onChange={e => setTimeframeMonths(Number(e.target.value))}>
                  <option value={12}>12 months</option>
                  <option value={24}>24 months</option>
                  <option value={36}>36 months</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Cost of inaction framing. Hidden when there is nothing to model. */}
        {totals.periodRecoverable > 0 && (
          <div className="card mb-4">
            <div className="flex items-start gap-3">
              <TrendingUp size={14} className="text-ink/55 mt-0.5 shrink-0" />
              <div>
                <div className="kpi-label mb-1">Cost of inaction</div>
                <div className="text-[13px] text-ink/85 leading-relaxed">
                  Over the next {timeframeMonths} months, doing nothing leaves <span className="font-medium">{fmtCurrency(totals.periodRecoverable)}</span> on the table.
                  One-off implementation of <span className="font-medium">{fmtCurrency(totals.totalCost)}</span> recovers <span className="font-medium">{fmtCurrency(totals.periodRecoverable - totals.totalCost)}</span> over that period.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Summary bar (KPIs) */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="kpi-card">
            <div className="kpi-label">Recoverable ({timeframeMonths}m)</div>
            <div className="kpi-value text-brand-green">{fmtCurrency(totals.periodRecoverable)}</div>
            <div className="text-[10.5px] text-ink/45 mt-1">
              {fmtCurrency(totals.low.periodRecoverable)}–{fmtCurrency(totals.high.periodRecoverable)} range
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Implementation cost</div>
            <div className="kpi-value">{fmtCurrency(totals.totalCost)}</div>
            <div className="text-[10.5px] text-ink/45 mt-1">One-off</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">ROI multiple</div>
            <div className="kpi-value">{totals.roiMultiple != null ? `${totals.roiMultiple.toFixed(1)}x` : '—'}</div>
            <div className="text-[10.5px] text-ink/45 mt-1">
              {totals.roiMultiple != null && totals.low.roiMultiple != null && totals.high.roiMultiple != null
                ? `${totals.low.roiMultiple.toFixed(1)}x – ${totals.high.roiMultiple.toFixed(1)}x range`
                : 'Period return ÷ cost'}
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Payback</div>
            <div className="kpi-value">{formatPayback(totals.paybackWeeks).primary}</div>
            <div className="text-[10.5px] text-ink/45 mt-1">{formatPayback(totals.paybackWeeks).secondary}</div>
          </div>
        </div>

        {/* Drivers table */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="section-title text-[13.5px]">Drivers</div>
            {mode === 'manual' && (
              <button onClick={addDriver} className="btn-ghost btn-xs"><Plus size={11}/> Add driver</button>
            )}
          </div>

          <table className="tbl">
            <thead>
              <tr>
                <th>Driver</th>
                <th className="text-right">Annual loss</th>
                <th>Recovery rate</th>
                <th className="text-right">Implementation cost</th>
                <th className="text-right">Net annual</th>
                {mode === 'manual' && <th></th>}
              </tr>
            </thead>
            <tbody>
              {drivers.map(d => {
                const recoverable = d.estimatedLoss * d.recoveryRate / 100
                const netAnnual = recoverable - d.implementationCost
                const meta = lookupDriverMeta(d.category)
                const matchedCeiling = (() => {
                  const c = (d.category || '').toLowerCase()
                  for (const [key, val] of Object.entries(RECOVERY_CEILING)) {
                    if (c.includes(key)) return val
                  }
                  return null
                })()
                const sliderMax = matchedCeiling ?? 95
                return (
                  <tr key={d.id}>
                    <td>
                      {mode === 'manual'
                        ? <input className="input py-1 text-[12px]" value={d.category} onChange={e => updateDriver(d.id, { category: e.target.value })} />
                        : <div className="flex items-center gap-2">
                            <span>{d.category}</span>
                            {meta && (
                              <span className="group relative inline-flex" tabIndex={0}>
                                <Info size={12} className="text-ink/40" aria-label={meta.explainer}>
                                  <title>{meta.explainer}</title>
                                </Info>
                                <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 hidden group-hover:block group-focus-within:block z-10 w-56 bg-ink text-white text-[11px] rounded-md px-2.5 py-1.5 shadow-md leading-snug pointer-events-none">
                                  {meta.explainer}
                                </span>
                              </span>
                            )}
                            {d.confidence && <span className={`tag ${d.confidence === 'high' ? 'tag-green' : d.confidence === 'medium' ? 'tag-amber' : 'tag-red'}`}>{d.confidence}</span>}
                          </div>
                      }
                    </td>
                    <td className="text-right">
                      <input
                        type="number"
                        className="input py-1 text-[12px] text-right font-mono w-32 ml-auto"
                        value={d.estimatedLoss || ''}
                        onChange={e => updateDriver(d.id, { estimatedLoss: Number(e.target.value) || 0 })}
                        placeholder="0"
                      />
                    </td>
                    <td className="min-w-[180px]">
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min={0}
                          max={sliderMax}
                          value={Math.min(d.recoveryRate, sliderMax)}
                          onChange={e => updateDriver(d.id, { recoveryRate: Number(e.target.value) })}
                          className="flex-1 accent-ink"
                        />
                        <span className="font-mono text-[11.5px] text-ink/70 w-10 text-right">{Math.min(d.recoveryRate, sliderMax)}%</span>
                      </div>
                      <div className="text-[10.5px] text-ink/45 mt-0.5 font-mono">{fmtCurrency(recoverable)} recoverable</div>
                      {matchedCeiling !== null && (
                        <div className="text-[10px] text-ink/40 mt-0.5">Capped at {matchedCeiling}%, industry-realistic for this driver</div>
                      )}
                    </td>
                    <td className="text-right">
                      <input
                        type="number"
                        className="input py-1 text-[12px] text-right font-mono w-32 ml-auto"
                        value={d.implementationCost || ''}
                        onChange={e => updateDriver(d.id, { implementationCost: Number(e.target.value) || 0 })}
                        placeholder="0"
                      />
                      {meta && (
                        <div className="text-[10.5px] text-ink/45 mt-0.5 font-mono">
                          Typical: {fmtCurrency(meta.costRange[0])}–{fmtCurrency(meta.costRange[1])}
                        </div>
                      )}
                    </td>
                    <td className={`text-right font-mono font-medium ${netAnnual >= 0 ? 'text-brand-green' : 'text-brand-red'}`}>
                      {fmtCurrency(netAnnual)}
                    </td>
                    {mode === 'manual' && (
                      <td className="text-right">
                        <button onClick={() => removeDriver(d.id)} className="text-ink/30 hover:text-brand-red transition-colors">
                          <Trash2 size={13}/>
                        </button>
                      </td>
                    )}
                  </tr>
                )
              })}
              {drivers.length === 0 && (
                <tr><td colSpan={mode === 'manual' ? 6 : 5} className="text-center text-ink/40 py-6">No drivers — {mode === 'manual' ? 'add one above' : 'select a diagnostic'}.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Method note */}
        <div className="narr mt-4">
          <strong className="text-ink/85">Method:</strong> Recoverable revenue = annual loss × recovery rate. Period recoverable scales by timeframe.
          ROI multiple = period recoverable ÷ implementation cost. Payback = cost ÷ monthly recoverable. Recovery rates default to category-typical values
          and should be adjusted with the operator. Figures are directional and depend on the underlying diagnostic confidence.
        </div>
      </div>
    </AppShell>
  )
}

// Smart time-unit formatting for payback. Days for very fast paybacks,
// weeks for the typical band, months for slow, years for outliers.
function formatPayback(weeks: number | null): { primary: string; secondary: string } {
  if (weeks == null) return { primary: '—', secondary: 'No cost entered' }
  const days = weeks * 7
  const months = weeks / 4.33
  if (days < 14) {
    return { primary: `${Math.round(days)}d`, secondary: `~${weeks.toFixed(1)} weeks` }
  }
  if (weeks < 52) {
    return { primary: `${weeks.toFixed(1)}w`, secondary: `~${months.toFixed(1)} months` }
  }
  return { primary: `${months.toFixed(1)}mo`, secondary: `~${(months / 12).toFixed(1)} years` }
}

// Heuristic default recovery rates by category
function defaultRecoveryRate(category: string): number {
  const c = (category || '').toLowerCase()
  if (c.includes('fx')) return 70
  if (c.includes('retry')) return 80
  if (c.includes('auth')) return 60
  if (c.includes('cross')) return 40
  if (c.includes('routing')) return 55
  if (c.includes('chargeback')) return 50
  if (c.includes('payment method')) return 35
  return 50
}
