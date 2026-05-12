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

// Plain-English explainers per driver category, surfaced as tooltips
// so merchants understand what each driver represents. Categories are
// matched fuzzily so diagnostic-derived names that vary slightly still
// resolve. Cost ranges intentionally absent: the new model defaults
// implementation cost to £0 and only introduces cost via the
// orchestration / advisory overlays.
const DRIVER_EXPLAINERS: Record<string, string> = {
  'authorisation':  'Approved transactions you are not capturing because the issuer declined.',
  'cross-border':   'Lost approvals on international transactions due to acquirer setup or routing.',
  'cross border':   'Lost approvals on international transactions due to acquirer setup or routing.',
  'fx':             'Margin lost to FX spread or settlement currency mismatch.',
  'retry':          'Soft declines that could be recovered with smarter retry timing or network tokens.',
  'routing':        'Performance loss from single-PSP dependency or absence of failover.',
  'chargeback':     'Operational overhead and revenue loss from disputes and refunds.',
  'payment method': 'Missed conversion from absent local payment methods in key markets.',
}

function explainerFor(category: string): string | null {
  const c = (category || '').toLowerCase()
  for (const [key, val] of Object.entries(DRIVER_EXPLAINERS)) {
    if (c.includes(key)) return val
  }
  return null
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

// Per-transaction orchestration fee tiers used to size the recurring
// cost when a merchant does not currently run orchestration. Tiers are
// volume-banded so smaller merchants see a higher per-tx rate (less
// negotiating leverage) and high-volume merchants see the wholesale
// rate. Tune in one place.
function orchestrationEstimate(monthlyTransactions: number | null | undefined) {
  if (!monthlyTransactions || monthlyTransactions <= 0) return null
  const perTx = monthlyTransactions < 100000
    ? 0.08
    : monthlyTransactions < 1000000
      ? 0.05
      : 0.02
  const annualCost = monthlyTransactions * 12 * perTx
  return { perTx, annualCost }
}

export default function RoiPage() {
  const [mode, setMode] = useState<Mode>('diagnostic')
  const [diagnostics, setDiagnostics] = useState<any[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [drivers, setDrivers] = useState<Driver[]>(DEFAULT_DRIVERS)
  const [timeframeMonths, setTimeframeMonths] = useState<number>(12)
  const [companyName, setCompanyName] = useState<string>('')
  const [monthlyTransactions, setMonthlyTransactions] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)
  const [demoActive, setDemoActive] = useState(false)
  // Sticky dismissal: hidden once across browser sessions.
  const [demoBannerDismissed, setDemoBannerDismissed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem('vyre_demo_banner_dismissed') === '1'
  })
  const dismissDemoBanner = () => {
    setDemoBannerDismissed(true)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('vyre_demo_banner_dismissed', '1')
    }
  }
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)
  // Cost overlays. null = overlay not added; 0 = added but empty;
  // any positive number = real fee. Math wiring lands in a follow-up
  // commit once the canonical totals replacement is finalised.
  const [orchestrationCost, setOrchestrationCost] = useState<number | null>(null)
  const [orchestrationNotes, setOrchestrationNotes] = useState<string>('')
  const [advisoryFee, setAdvisoryFee] = useState<number | null>(null)

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

  // Auto-select the most recent released diagnostic so the ROI page
  // lands on real data straight away rather than a "Select a diagnostic"
  // dropdown with zero KPIs underneath.
  useEffect(() => {
    if (loading || mode !== 'diagnostic' || selectedId || diagnostics.length === 0) return
    setSelectedId(diagnostics[0].id)
  }, [loading, mode, selectedId, diagnostics])

  // Demo mode: enter once when the dashboard has no released diagnostics
  // so the calculator never lands empty for first-time visitors.
  useEffect(() => {
    if (loading || demoActive) return
    if (mode === 'diagnostic' && diagnostics.length === 0 && !selectedId) {
      setDrivers(DEMO_DRIVERS)
      setCompanyName(DEMO_COMPANY)
      setTimeframeMonths(12)
      setMonthlyTransactions(120000)  // mid-market UK retailer baseline
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
      setMonthlyTransactions(null)
      setDemoActive(false)
      setOrchestrationCost(null)
      setOrchestrationNotes('')
      setAdvisoryFee(null)
    }
  }, [demoActive, selectedId, mode])

  // When a diagnostic is selected, hydrate drivers from financial_breakdown
  useEffect(() => {
    if (mode !== 'diagnostic' || !selectedId) return
    const d = diagnostics.find(x => x.id === selectedId)
    if (!d) return
    setCompanyName(d.organisation?.name || d.company_name || d.reference || '')
    setMonthlyTransactions(d.monthly_transactions ?? null)
    const breakdown = d.output?.financial_breakdown || []
    if (breakdown.length === 0) {
      setDrivers(DEFAULT_DRIVERS)
      return
    }
    // Production AI output uses estimated_loss_mid (and _low / _high)
    // per the prompt schema; older / hand-crafted fixtures sometimes
    // carry a singular estimated_loss. Accept either.
    const next: Driver[] = breakdown.map((b: any, i: number) => ({
      id: `b${i}`,
      category: b.category || `Driver ${i + 1}`,
      estimatedLoss: Number(b.estimated_loss ?? b.estimated_loss_mid ?? 0) || 0,
      recoveryRate: Math.min(defaultRecoveryRate(b.category), ceilingFor(b.category)),
      implementationCost: 0,
      confidence: b.confidence,
    }))
    setDrivers(next)
  }, [mode, selectedId, diagnostics])

  // Computed totals. The new £0-default model: drivers carry no cost,
  // orchestration overlay reduces gross recovery to net (recurring),
  // advisory overlay is the only one-off. Mid case drives the headline
  // numbers; low and high bracket the recovery rate by ±0.6 / ×1.2
  // (capped at each driver's ceiling). Implementation cost equals the
  // advisory fee; ROI / payback only resolve to numbers when a one-off
  // is present.
  const totals = useMemo(() => {
    const orchAnnual = orchestrationCost ?? 0
    const oneOffCost = advisoryFee ?? 0
    // Visible overlay rows with no value typed yet should not flip the page
    // out of pure-recovery framing. Flip only once a real number is entered.
    const hasAnyCost = orchAnnual > 0 || oneOffCost > 0

    const grossAnnualForFactor = (factor: number) =>
      drivers.reduce((sum, d) => {
        const rate = factor === 1
          ? d.recoveryRate
          : Math.min(d.recoveryRate * factor, ceilingFor(d.category))
        return sum + (d.estimatedLoss * rate / 100)
      }, 0)

    const buildCase = (factor: number) => {
      const grossAnnual = grossAnnualForFactor(factor)
      const netAnnual = Math.max(0, grossAnnual - orchAnnual)
      const periodRecoverable = netAnnual * (timeframeMonths / 12)
      const monthlyRecoverable = netAnnual / 12
      return {
        grossAnnual,
        netAnnual,
        annualRecoverable: netAnnual,
        periodRecoverable,
        roiMultiple: oneOffCost > 0 ? periodRecoverable / oneOffCost : null,
        paybackWeeks: oneOffCost > 0 && monthlyRecoverable > 0
          ? (oneOffCost / monthlyRecoverable) * (52 / 12)
          : null,
      }
    }

    const low = buildCase(0.6)
    const mid = buildCase(1)
    const high = buildCase(1.2)

    const grossPeriod = mid.grossAnnual * (timeframeMonths / 12)

    return {
      annualRecoverable: mid.netAnnual,
      grossAnnualRecoverable: mid.grossAnnual,
      grossPeriodRecoverable: grossPeriod,
      netAnnualRecoverable: mid.netAnnual,
      totalCost: oneOffCost,
      orchAnnual,
      oneOffCost,
      hasAnyCost,
      periodRecoverable: mid.periodRecoverable,
      netGain: mid.periodRecoverable - oneOffCost,
      roiMultiple: mid.roiMultiple,
      paybackWeeks: mid.paybackWeeks,
      low,
      high,
    }
  }, [drivers, timeframeMonths, orchestrationCost, advisoryFee])

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
    setMonthlyTransactions(120000)
    setOrchestrationCost(null)
    setOrchestrationNotes('')
    setAdvisoryFee(null)
  }

  const copySummary = async () => {
    const lines = [
      `Outturn ROI Summary${companyName ? ` — ${companyName}` : ''}`,
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
      const costState = !totals.hasAnyCost
        ? 'pure_recovery'
        : totals.orchAnnual > 0 && totals.oneOffCost === 0
          ? 'orchestration_only'
          : totals.orchAnnual === 0 && totals.oneOffCost > 0
            ? 'advisory_only'
            : 'both'
      const res = await reportsApi.roiPdf({
        companyName: companyName || 'Scenario',
        timeframeMonths,
        drivers,
        totals: {
          grossPeriodRecoverable: totals.grossPeriodRecoverable,
          periodRecoverable: totals.periodRecoverable,
          totalCost: totals.totalCost,
          orchAnnual: totals.orchAnnual,
          oneOffCost: totals.oneOffCost,
          roiMultiple: totals.roiMultiple,
          paybackWeeks: totals.paybackWeeks,
        },
        scenarioRange: {
          lowRecoverable: totals.low.periodRecoverable,
          highRecoverable: totals.high.periodRecoverable,
          lowRoi: totals.low.roiMultiple,
          highRoi: totals.high.roiMultiple,
        },
        costOverlay: totals.hasAnyCost ? {
          orchestrationAnnualCost: orchestrationCost,
          orchestrationNotes,
          advisoryFee,
        } : null,
        costState,
      })
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const slug = (companyName || 'scenario').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'scenario'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `vyre-roi-${slug}.pdf`
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
                onClick={dismissDemoBanner}
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

        {/* Cost of inaction framing. Copy adapts to the four overlay
            permutations (pure / orch-only / advisory-only / both).
            Hidden when there is no recoverable revenue to model. */}
        {totals.grossPeriodRecoverable > 0 && (
          <div className="card mb-4">
            <div className="flex items-start gap-3">
              <TrendingUp size={14} className="text-ink/55 mt-0.5 shrink-0" />
              <div>
                <div className="kpi-label mb-1">Cost of inaction</div>
                <div className="text-[13px] text-ink/85 leading-relaxed">
                  Over the next {timeframeMonths} months, doing nothing leaves <span className="font-medium">{fmtCurrency(totals.grossPeriodRecoverable)}</span> on the table.{' '}
                  {!totals.hasAnyCost && (
                    <>Resolvable by adding a layer with the right payment strategy, shifting the power dynamic back into your control, not the legacy providers.</>
                  )}
                  {totals.hasAnyCost && totals.orchAnnual > 0 && totals.oneOffCost === 0 && (
                    <>Recovering it requires <span className="font-medium">{fmtCurrency(totals.orchAnnual)}/year</span> in orchestration fees, netting <span className="font-medium">{fmtCurrency(totals.periodRecoverable)}</span> over that period.</>
                  )}
                  {totals.hasAnyCost && totals.orchAnnual === 0 && totals.oneOffCost > 0 && (
                    <>One-off advisory of <span className="font-medium">{fmtCurrency(totals.oneOffCost)}</span> recovers <span className="font-medium">{fmtCurrency(totals.periodRecoverable - totals.oneOffCost)}</span> net.</>
                  )}
                  {totals.hasAnyCost && totals.orchAnnual > 0 && totals.oneOffCost > 0 && (
                    <><span className="font-medium">{fmtCurrency(totals.oneOffCost)}</span> advisory plus <span className="font-medium">{fmtCurrency(totals.orchAnnual)}/year</span> fees recover <span className="font-medium">{fmtCurrency(totals.periodRecoverable - totals.oneOffCost)}</span> net.</>
                  )}
                </div>
                {!totals.hasAnyCost && (
                  <div className="text-[12.5px] text-ink/70 leading-relaxed mt-2 pt-2 border-t border-ink/10">
                    Speak to a Outturn Strategic AE who is provider-agnostic, with the integrity and expertise to map your leakage end to end, build a strategy that works for you and not the providers, and connect you with the right partner of choice.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Summary bar (KPIs). Pure-recovery frame when no costs are active;
            classic implementation/ROI/payback frame once an overlay introduces a cost. */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="kpi-card">
            <div className="kpi-label">Recoverable ({timeframeMonths}m)</div>
            <div className="kpi-value text-brand-green">{fmtCurrency(totals.periodRecoverable)}</div>
            <div className="text-[10.5px] text-ink/45 mt-1">
              {fmtCurrency(totals.low.periodRecoverable)}–{fmtCurrency(totals.high.periodRecoverable)} range
            </div>
          </div>
          {totals.hasAnyCost ? (
            <>
              <div className="kpi-card">
                <div className="kpi-label">Implementation cost</div>
                <div className="kpi-value">{fmtCurrency(totals.oneOffCost)}</div>
                <div className="text-[10.5px] text-ink/45 mt-1">
                  {totals.orchAnnual > 0 ? `One-off, plus ${fmtCurrency(totals.orchAnnual)}/yr` : 'One-off'}
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">ROI multiple</div>
                {totals.oneOffCost > 0 ? (
                  <>
                    <div className="kpi-value">{totals.roiMultiple != null ? `${totals.roiMultiple.toFixed(1)}x` : '—'}</div>
                    <div className="text-[10.5px] text-ink/45 mt-1">
                      {totals.low.roiMultiple != null && totals.high.roiMultiple != null
                        ? `${totals.low.roiMultiple.toFixed(1)}x – ${totals.high.roiMultiple.toFixed(1)}x range`
                        : 'Period return ÷ cost'}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="kpi-value text-[16px]">Pure recovery (after fees)</div>
                    <div className="text-[10.5px] text-ink/45 mt-1">{fmtCurrency(totals.orchAnnual)}/yr orchestration</div>
                  </>
                )}
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Payback</div>
                {totals.oneOffCost > 0 ? (
                  <>
                    <div className="kpi-value">{formatPayback(totals.paybackWeeks).primary}</div>
                    <div className="text-[10.5px] text-ink/45 mt-1">{formatPayback(totals.paybackWeeks).secondary}</div>
                  </>
                ) : (
                  <>
                    <div className="kpi-value text-[18px]">Immediately</div>
                    <div className="text-[10.5px] text-ink/45 mt-1">No one-off cost</div>
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="kpi-card">
                <div className="kpi-label">Cost to recover</div>
                <div className="kpi-value flex items-center gap-2">
                  <span>£0</span>
                  <span className="tag tag-green">Pure recovery</span>
                </div>
                <div className="text-[10.5px] text-ink/45 mt-1">No spend required</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Recovery type</div>
                <div className="kpi-value text-[18px]">Pure recovery</div>
                <div className="text-[10.5px] text-ink/45 mt-1">Configuration and vendor changes</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Recovery starts</div>
                <div className="kpi-value text-[18px]">Immediately</div>
                <div className="text-[10.5px] text-ink/45 mt-1">No payback period</div>
              </div>
            </>
          )}
        </div>

        {/* Cost overlays. Two opt-in costs that the operator layers on top
            of the pure-recovery base. Math wiring lands in a follow-up. */}
        {(orchestrationCost !== null || advisoryFee !== null) && (
          <div className="space-y-3 mb-4">
            {orchestrationCost !== null && (
              <div className="card py-3">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="section-title text-[12.5px]">Orchestration adoption, recurring</div>
                  <button
                    onClick={() => { setOrchestrationCost(null); setOrchestrationNotes('') }}
                    className="text-ink/30 hover:text-brand-red transition-colors"
                    aria-label="Remove orchestration overlay"
                  >
                    <X size={13}/>
                  </button>
                </div>
                <div className="form-grid-2">
                  <div>
                    <label className="label">Annual run-rate cost (£)</label>
                    <input
                      type="number"
                      className="input"
                      value={orchestrationCost || ''}
                      onChange={e => setOrchestrationCost(Number(e.target.value) || 0)}
                      placeholder="0"
                    />
                  </div>
                  <div>
                    <label className="label">Notes</label>
                    <input
                      className="input"
                      value={orchestrationNotes}
                      onChange={e => setOrchestrationNotes(e.target.value)}
                      placeholder="e.g. Primer @ 0.12% × £5m/mo"
                    />
                  </div>
                </div>
              </div>
            )}
            {advisoryFee !== null && (
              <div className="card py-3">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="section-title text-[12.5px]">Outturn advisory, one-off</div>
                  <button
                    onClick={() => setAdvisoryFee(null)}
                    className="text-ink/30 hover:text-brand-red transition-colors"
                    aria-label="Remove advisory overlay"
                  >
                    <X size={13}/>
                  </button>
                </div>
                <div className="form-grid-2">
                  <div>
                    <label className="label">Fee (£)</label>
                    <input
                      type="number"
                      className="input"
                      value={advisoryFee || ''}
                      onChange={e => setAdvisoryFee(Number(e.target.value) || 0)}
                      placeholder="0"
                    />
                  </div>
                  <div></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Drivers table */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 gap-3">
            <div className="section-title text-[13.5px]">Drivers</div>
            <div className="flex items-center gap-2">
              {orchestrationCost === null && (
                <button onClick={() => setOrchestrationCost(0)} className="btn-ghost btn-sm">
                  <Plus size={13}/> Orchestration cost
                </button>
              )}
              {advisoryFee === null && (
                <button onClick={() => setAdvisoryFee(0)} className="btn-ghost btn-sm">
                  <Plus size={13}/> Advisory fee
                </button>
              )}
              {mode === 'manual' && (
                <button onClick={addDriver} className="btn-ghost btn-xs"><Plus size={11}/> Add driver</button>
              )}
            </div>
          </div>

          <table className="tbl">
            <thead>
              <tr>
                <th>Driver</th>
                <th className="text-right">Annual loss</th>
                <th>Recovery rate</th>
                <th className="text-right">Net annual</th>
                {mode === 'manual' && <th></th>}
              </tr>
            </thead>
            <tbody>
              {drivers.map(d => {
                const recoverable = d.estimatedLoss * d.recoveryRate / 100
                const netAnnual = recoverable - d.implementationCost
                const explainer = explainerFor(d.category)
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
                            {explainer && (
                              <span className="group relative inline-flex" tabIndex={0}>
                                <Info size={12} className="text-ink/40" aria-label={explainer}>
                                  <title>{explainer}</title>
                                </Info>
                                <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1 hidden group-hover:block group-focus-within:block z-10 w-56 bg-ink text-white text-[11px] rounded-md px-2.5 py-1.5 shadow-md leading-snug pointer-events-none">
                                  {explainer}
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
                    <td className={`text-right font-mono font-medium ${recoverable >= 0 ? 'text-brand-green' : 'text-brand-red'}`}>
                      {fmtCurrency(recoverable)}
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
                <tr><td colSpan={4 + (mode === 'manual' ? 1 : 0)} className="text-center text-ink/40 py-6">No drivers, {mode === 'manual' ? 'add one above' : 'select a diagnostic'}.</td></tr>
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
