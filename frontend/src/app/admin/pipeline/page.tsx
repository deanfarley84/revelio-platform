'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { adminApi } from '@/lib/api'
import { RefreshCw, AlertTriangle, CheckCircle, Loader } from 'lucide-react'

export default function PipelinePage() {
  const [jobs, setJobs] = useState<any[]>([])
  const [pipeline, setPipeline] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      const [pipelineRes, jobsRes] = await Promise.all([
        adminApi.overview(),
        adminApi.jobs(),
      ])
      setPipeline(pipelineRes.data.pipeline || [])
      setJobs(jobsRes.data || [])
    } catch {}
    setLoading(false)
    setRefreshing(false)
  }

  useEffect(() => { load() }, [])

  const refresh = () => { setRefreshing(true); load() }

  const statusIcon = (s: string) => {
    if (s === 'running') return <Loader size={13} className="text-brand-blue animate-spin" />
    if (s === 'complete') return <CheckCircle size={13} className="text-brand-green" />
    if (s === 'failed') return <AlertTriangle size={13} className="text-brand-red" />
    return <div className="w-3 h-3 rounded-full bg-surface-3 border border-black/10" />
  }

  const statusTag = (s: string) => {
    const map: Record<string, string> = {
      running: 'tag-blue', complete: 'tag-green', failed: 'tag-red',
      queued: 'tag-gray', cancelled: 'tag-gray'
    }
    return map[s] || 'tag-gray'
  }

  const diagStageTag = (s: string) => {
    const map: Record<string, string> = {
      draft: 'tag-gray', submitted: 'tag-blue', validating: 'tag-blue',
      processing: 'tag-blue', ai_complete: 'tag-blue', pending_review: 'tag-amber',
      revision_requested: 'tag-red', approved: 'tag-green', released: 'tag-green', rejected: 'tag-red'
    }
    return map[s] || 'tag-gray'
  }

  if (loading) return <AppShell><div className="text-[13px] text-ink/40 py-12 text-center">Loading pipeline...</div></AppShell>

  return (
    <AppShell>
      <div className="max-w-5xl">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="section-title">Analysis pipeline</div>
            <div className="section-sub">Background job status and diagnostic processing queue</div>
          </div>
          <button onClick={refresh} disabled={refreshing} className="btn-ghost btn-sm">
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Diagnostic pipeline */}
        <div className="card mb-4">
          <div className="text-[13px] font-medium mb-4">Diagnostic pipeline</div>
          {pipeline.length === 0 ? (
            <p className="text-[12px] text-ink/40 py-4 text-center">No active diagnostics</p>
          ) : (
            <table className="tbl">
              <thead>
                <tr><th>Reference</th><th>Client</th><th>Tier</th><th>Current stage</th><th>Submitted</th><th>Confidence</th><th>Status</th></tr>
              </thead>
              <tbody>
                {pipeline.map((d: any) => (
                  <tr key={d.id}>
                    <td className="font-mono text-[11px]">{d.reference}</td>
                    <td className="font-medium">{d.company_name}</td>
                    <td><span className={`tier-${d.tier}`}>{d.tier?.toUpperCase()}</span></td>
                    <td className="capitalize text-[11.5px] text-ink/70">{d.status?.replace(/_/g, ' ')}</td>
                    <td className="text-[11.5px] text-ink/50">
                      {d.submitted_at ? new Date(d.submitted_at).toLocaleDateString('en-GB', { day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' }) : '—'}
                    </td>
                    <td>
                      {d.confidence_level ? (
                        <span className={`text-[11px] font-medium capitalize ${d.confidence_level === 'high' ? 'text-brand-green' : d.confidence_level === 'medium' ? 'text-brand-amber' : 'text-brand-red'}`}>
                          {d.confidence_level}
                        </span>
                      ) : '—'}
                    </td>
                    <td><span className={`tag ${diagStageTag(d.status)} text-[10px]`}>{d.status?.replace(/_/g, ' ')}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Background jobs */}
        <div className="card">
          <div className="text-[13px] font-medium mb-4">Background jobs</div>
          {jobs.length === 0 ? (
            <p className="text-[12px] text-ink/40 py-4 text-center">No recent jobs</p>
          ) : (
            <table className="tbl">
              <thead>
                <tr><th>Job ID</th><th>Type</th><th>Diagnostic</th><th>Status</th><th>Retries</th><th>Queued</th><th>Completed</th></tr>
              </thead>
              <tbody>
                {jobs.map((j: any) => (
                  <tr key={j.id}>
                    <td className="font-mono text-[10.5px] text-ink/50">{j.id?.slice(0,8)}...</td>
                    <td>
                      <span className="tag tag-gray text-[10px]">{j.job_type?.replace(/_/g, ' ')}</span>
                    </td>
                    <td className="font-mono text-[11px] text-ink/50">{j.diagnostic_id?.slice(0,8) || '—'}...</td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        {statusIcon(j.status)}
                        <span className={`tag ${statusTag(j.status)} text-[10px]`}>{j.status}</span>
                      </div>
                    </td>
                    <td className="text-ink/50 text-[12px]">{j.retry_count}</td>
                    <td className="text-[11px] text-ink/40">
                      {j.queued_at ? new Date(j.queued_at).toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }) : '—'}
                    </td>
                    <td className="text-[11px] text-ink/40">
                      {j.completed_at ? new Date(j.completed_at).toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' }) : j.status === 'running' ? <span className="text-brand-blue animate-pulse">Running...</span> : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {jobs.some((j: any) => j.error_message) && (
            <div className="mt-4 space-y-2">
              <div className="text-[11px] font-medium text-brand-red uppercase tracking-wider">Failed job errors</div>
              {jobs.filter((j: any) => j.error_message).map((j: any) => (
                <div key={j.id} className="alert-red text-[11.5px]">
                  <AlertTriangle size={12} />
                  <span><strong>{j.job_type}:</strong> {j.error_message}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline stages legend */}
        <div className="card mt-4">
          <div className="text-[12px] font-medium mb-3">Pipeline stages</div>
          <div className="grid grid-cols-5 gap-3">
            {[
              { stage: '1. Submit', desc: 'Client submits data or files', color: 'bg-surface-3' },
              { stage: '2. Validate', desc: 'Input completeness check', color: 'bg-brand-blue-bg' },
              { stage: '3. AI analysis', desc: 'Claude processes via prompt engine', color: 'bg-brand-blue-bg' },
              { stage: '4. Pending review', desc: 'Awaiting operator approval', color: 'bg-brand-amber-bg' },
              { stage: '5. Released', desc: 'Report visible to client', color: 'bg-brand-green-bg' },
            ].map(({ stage, desc, color }) => (
              <div key={stage} className={`${color} rounded-lg p-3`}>
                <div className="text-[11.5px] font-medium mb-1">{stage}</div>
                <div className="text-[10.5px] text-ink/50">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
