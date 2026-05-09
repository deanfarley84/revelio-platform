'use client'
import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import AppShell from '@/components/layout/AppShell'
import { diagnosticsApi, filesApi } from '@/lib/api'
import { Upload, FileText, CheckCircle, AlertCircle, X, ArrowRight } from 'lucide-react'
import { useRouter } from 'next/navigation'

const ACCEPT = { 'text/csv': ['.csv'], 'application/vnd.ms-excel': ['.xls'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'], 'application/pdf': ['.pdf'], 'text/plain': ['.txt'] }

interface UploadedFile { file: File; status: 'pending' | 'uploading' | 'parsed' | 'error'; parsedFields?: Record<string, any>; confidence?: number }
interface ParsedPreview { [key: string]: any }

export default function SubmitPage() {
  const router = useRouter()
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [diagId, setDiagId] = useState<string | null>(null)
  const [parsedPreview, setParsedPreview] = useState<ParsedPreview | null>(null)
  const [formData, setFormData] = useState({ company_name: '', website: '', vertical: 'retail', tier: 'core' })
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState<'upload' | 'review' | 'submitting' | 'done'>('upload')

  const ensureDiagnostic = async () => {
    if (diagId) return diagId
    const res = await diagnosticsApi.create({ ...formData, monthly_volume: null })
    setDiagId(res.data.id)
    return res.data.id
  }

  const onDrop = useCallback(async (accepted: File[]) => {
    const id = await ensureDiagnostic()
    const newFiles = accepted.map(f => ({ file: f, status: 'uploading' as const }))
    setFiles(prev => [...prev, ...newFiles])

    for (let i = 0; i < accepted.length; i++) {
      try {
        const res = await filesApi.upload(id, accepted[i])
        const { id: fileId, parsed_fields, parse_confidence } = res.data
        setFiles(prev => prev.map((f, idx) =>
          f.file === accepted[i] ? { ...f, status: 'parsed', parsedFields: parsed_fields, confidence: parse_confidence } : f
        ))
        // Merge into preview
        setParsedPreview(prev => ({ ...(prev || {}), ...(parsed_fields || {}) }))
        if (i === accepted.length - 1) setStep('review')
      } catch {
        setFiles(prev => prev.map(f => f.file === accepted[i] ? { ...f, status: 'error' } : f))
      }
    }
  }, [diagId, formData])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: ACCEPT, maxSize: 20 * 1024 * 1024 })

  const removeFile = (idx: number) => setFiles(prev => prev.filter((_, i) => i !== idx))

  const handleSubmit = async () => {
    if (!diagId) return
    setSubmitting(true)
    setStep('submitting')
    try {
      // Apply parsed fields back to diagnostic
      if (parsedPreview) {
        const update: any = {}
        if (parsedPreview.monthly_volume) update.monthly_volume = parsedPreview.monthly_volume
        if (parsedPreview.auth_rate) update.auth_rate = parsedPreview.auth_rate
        if (parsedPreview.decline_rate) update.decline_rate = parsedPreview.decline_rate
        if (parsedPreview.chargeback_rate) update.chargeback_rate = parsedPreview.chargeback_rate
        if (parsedPreview.monthly_transactions) update.monthly_transactions = parsedPreview.monthly_transactions
        await diagnosticsApi.create({ ...formData, ...update, id: diagId })
      }
      await diagnosticsApi.submit(diagId)
      setStep('done')
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Submission failed')
      setStep('review')
    }
    setSubmitting(false)
  }

  const fieldLabels: Record<string, string> = {
    monthly_volume: 'Monthly volume (£)', auth_rate: 'Auth rate (%)', decline_rate: 'Decline rate (%)',
    chargeback_rate: 'Chargeback rate (%)', monthly_transactions: 'Monthly transactions',
    avg_order_value: 'Avg. order value (£)', cross_border_pct: 'Cross-border (%)',
    fx_fee_spread: 'FX spread (%)', mdr: 'MDR (%)', psp_detected: 'PSP detected',
  }

  if (step === 'done') return (
    <AppShell>
      <div className="max-w-lg mx-auto mt-16 text-center">
        <div className="w-14 h-14 rounded-full bg-brand-green-bg flex items-center justify-center mx-auto mb-4">
          <CheckCircle size={24} className="text-brand-green" />
        </div>
        <h1 className="text-xl font-medium mb-2">Diagnostic submitted</h1>
        <p className="text-[13px] text-ink/50 mb-2">Your data is being analysed. We'll notify you when your report is ready.</p>
        <p className="text-[12px] text-ink/40 font-mono mb-6">Reference: {diagId}</p>
        <button onClick={() => router.push('/dashboard')} className="btn-primary">Go to dashboard <ArrowRight size={13} /></button>
      </div>
    </AppShell>
  )

  return (
    <AppShell>
      <div className="max-w-5xl">
        <div className="alert-blue mb-5">
          <Upload size={13} />
          Upload your payment data — we extract fields automatically. Review before submitting.
        </div>

        <div className="grid grid-cols-2 gap-5">
          <div>
            {/* Company details */}
            <div className="card mb-4">
              <div className="text-[13px] font-medium mb-3">Company details</div>
              <div className="form-row">
                <label className="label">Company name *</label>
                <input className="input" value={formData.company_name} onChange={e => setFormData(p => ({ ...p, company_name: e.target.value }))} placeholder="e.g. Acme Retail Ltd" />
              </div>
              <div className="form-grid-2">
                <div className="form-row">
                  <label className="label">Website</label>
                  <input className="input" value={formData.website} onChange={e => setFormData(p => ({ ...p, website: e.target.value }))} placeholder="acme.com" />
                </div>
                <div className="form-row">
                  <label className="label">Sector *</label>
                  <select className="input" value={formData.vertical} onChange={e => setFormData(p => ({ ...p, vertical: e.target.value }))}>
                    <option value="retail">Retail – General</option>
                    <option value="saas">SaaS / Subscription</option>
                    <option value="travel">Travel</option>
                    <option value="marketplace">Marketplace</option>
                    <option value="fintech">Financial Services</option>
                    <option value="luxury">Luxury / High-ticket</option>
                  </select>
                </div>
              </div>
              <div className="form-row">
                <label className="label">Service tier *</label>
                <select className="input" value={formData.tier} onChange={e => setFormData(p => ({ ...p, tier: e.target.value }))}>
                  <option value="lite">Lite – Fast entry diagnostic</option>
                  <option value="core">Core – Full diagnostic</option>
                  <option value="enterprise">Enterprise – Precision analysis</option>
                </select>
              </div>
            </div>

            {/* Upload zone */}
            <div className="card">
              <div className="text-[13px] font-medium mb-1">Upload payment data</div>
              <div className="text-[11.5px] text-ink/40 mb-3">CSV, Excel, PDF statements — we extract fields automatically</div>
              <div {...getRootProps()} className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${isDragActive ? 'border-brand-blue bg-brand-blue-bg' : 'border-black/[0.13] hover:border-brand-blue hover:bg-brand-blue-bg/50'}`}>
                <input {...getInputProps()} />
                <div className="w-10 h-10 bg-surface-2 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <Upload size={18} className="text-ink/40" />
                </div>
                <div className="text-[13px] font-medium mb-1">{isDragActive ? 'Drop files here' : 'Drop files here or click to upload'}</div>
                <div className="text-[11.5px] text-ink/40 mb-3">PSP statements · Dashboard exports · Settlement reports</div>
                <div className="flex gap-1.5 justify-center flex-wrap">
                  {['CSV', 'XLSX', 'XLS', 'PDF', 'TXT'].map(f => <span key={f} className="bg-surface-2 text-ink/50 text-[10px] font-mono font-bold px-2 py-0.5 rounded">{f}</span>)}
                </div>
              </div>

              {/* File list */}
              {files.length > 0 && (
                <div className="mt-3 space-y-2">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2.5 p-2.5 bg-surface-2 rounded-lg">
                      <div className={`w-7 h-7 rounded-md flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${f.file.name.endsWith('.pdf') ? 'bg-brand-red-bg text-brand-red' : 'bg-brand-green-bg text-brand-green'}`}>
                        {f.file.name.split('.').pop()?.toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] font-medium truncate">{f.file.name}</div>
                        <div className="text-[10.5px] text-ink/40">{(f.file.size / 1024).toFixed(0)} KB</div>
                      </div>
                      {f.status === 'uploading' && <span className="text-[10.5px] text-brand-blue animate-pulse">Parsing...</span>}
                      {f.status === 'parsed' && <CheckCircle size={14} className="text-brand-green flex-shrink-0" />}
                      {f.status === 'error' && <AlertCircle size={14} className="text-brand-red flex-shrink-0" />}
                      <button onClick={() => removeFile(i)} className="text-ink/30 hover:text-ink/60 ml-1"><X size={13} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-4">
            {/* How it works */}
            {step === 'upload' && (
              <div className="card">
                <div className="text-[13px] font-medium mb-4">How it works</div>
                {[
                  ['Upload or enter data', 'CSV, Excel, PDF, or manual fields'],
                  ['AI analyses your stack', 'Claude identifies leakage across 7 categories'],
                  ['Expert review', 'Operator validates and approves findings'],
                  ['Download your report', 'Executive PDF with financial breakdown'],
                ].map(([title, sub], i) => (
                  <div key={i} className="flex gap-3 mb-4 last:mb-0">
                    <div className="w-6 h-6 rounded-full bg-ink text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">{i + 1}</div>
                    <div><div className="text-[12.5px] font-medium">{title}</div><div className="text-[11.5px] text-ink/50">{sub}</div></div>
                  </div>
                ))}
              </div>
            )}

            {/* Parsed preview */}
            {parsedPreview && Object.keys(parsedPreview).length > 0 && (
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-[13px] font-medium">Extracted data</div>
                  <span className="tag tag-green">Auto-filled</span>
                </div>
                <div className="bg-brand-green-bg border border-brand-green/20 rounded-lg p-3 mb-3">
                  <div className="text-[12px] font-medium text-brand-green mb-2">Fields detected and extracted</div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(parsedPreview).filter(([, v]) => v != null).map(([k, v]) => (
                      <div key={k} className="bg-white/60 rounded p-2">
                        <div className="text-[10px] text-brand-green uppercase tracking-wide font-medium mb-0.5">{fieldLabels[k] || k}</div>
                        <div className="text-[12px] font-medium text-ink">{typeof v === 'number' ? v.toLocaleString() : String(v)}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => router.push('/submit/manual')} className="btn-ghost btn-sm flex-1">Edit data</button>
                  <button onClick={handleSubmit} disabled={submitting} className="btn-primary flex-1">
                    {submitting ? 'Submitting...' : 'Submit for analysis →'}
                  </button>
                </div>
              </div>
            )}

            {step === 'upload' && files.length === 0 && (
              <div className="card">
                <div className="text-[13px] font-medium mb-2">Prefer to enter data manually?</div>
                <div className="text-[12px] text-ink/50 mb-3">Enter your payment metrics directly into our structured form.</div>
                <button onClick={() => router.push('/submit/manual')} className="btn-ghost w-full justify-center">Go to manual entry →</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
