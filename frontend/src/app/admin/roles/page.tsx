'use client'
import React from 'react'
import AppShell from '@/components/layout/AppShell'
import { CheckCircle, XCircle, ShieldAlert } from 'lucide-react'

const ROLES = [
  {
    role: 'Super Admin', key: 'super_admin', desc: 'Full system control — all capabilities',
    permissions: { submit: true, view_own: true, view_all: true, review_ai: true, approve: true, override: true, admin: true, intel: true, benchmarks: true, audit: true }
  },
  {
    role: 'Operator Admin', key: 'operator_admin', desc: 'Can review, approve, override, manage clients',
    permissions: { submit: true, view_own: true, view_all: true, review_ai: true, approve: true, override: true, admin: 'partial', intel: true, benchmarks: true, audit: false }
  },
  {
    role: 'Analyst', key: 'analyst', desc: 'Can review AI output and client data — read only',
    permissions: { submit: false, view_own: false, view_all: true, review_ai: true, approve: false, override: false, admin: false, intel: 'read', benchmarks: false, audit: false }
  },
  {
    role: 'Client Admin', key: 'client_admin', desc: 'Can submit diagnostics and view own released reports',
    permissions: { submit: true, view_own: true, view_all: false, review_ai: false, approve: false, override: false, admin: false, intel: false, benchmarks: false, audit: false }
  },
  {
    role: 'Client Viewer', key: 'client_viewer', desc: 'Read-only access to released reports for own organisation',
    permissions: { submit: false, view_own: 'released only', view_all: false, review_ai: false, approve: false, override: false, admin: false, intel: false, benchmarks: false, audit: false }
  },
]

const COLS = [
  { key: 'submit', label: 'Submit data' },
  { key: 'view_own', label: 'View own results' },
  { key: 'view_all', label: 'View all clients' },
  { key: 'review_ai', label: 'Review AI output' },
  { key: 'approve', label: 'Approve & release' },
  { key: 'override', label: 'Override values' },
  { key: 'admin', label: 'Admin panel' },
  { key: 'intel', label: 'Client intelligence' },
  { key: 'benchmarks', label: 'Edit benchmarks' },
  { key: 'audit', label: 'Audit log' },
]

function PermCell({ value }: { value: boolean | string }) {
  if (value === true) return <div className="flex justify-center"><CheckCircle size={14} className="text-brand-green" /></div>
  if (value === false) return <div className="flex justify-center"><XCircle size={14} className="text-ink/20" /></div>
  return <div className="flex justify-center"><span className="tag tag-amber text-[9.5px] capitalize">{String(value)}</span></div>
}

export default function RolesPage() {
  return (
    <AppShell>
      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="section-title">Roles &amp; permissions</div>
            <div className="section-sub">Access control model across all five role types</div>
          </div>
          <div className="flex items-center gap-2 text-[11.5px] text-brand-amber bg-brand-amber-bg border border-brand-amber/20 rounded-lg px-3 py-2">
            <ShieldAlert size={13} />
            Role assignment managed in user settings — contact Super Admin
          </div>
        </div>

        <div className="card mb-5 overflow-x-auto">
          <table className="tbl" style={{ tableLayout: 'fixed', minWidth: '900px' }}>
            <thead>
              <tr>
                <th style={{ width: '160px', textAlign: 'left' }}>Role</th>
                {COLS.map(c => <th key={c.key} style={{ width: '82px', textAlign: 'center' }}>{c.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {ROLES.map(r => (
                <tr key={r.key}>
                  <td>
                    <div className="font-medium text-[12.5px]">{r.role}</div>
                    <div className="text-[10.5px] text-ink/40 mt-0.5">{r.desc}</div>
                  </td>
                  {COLS.map(c => (
                    <td key={c.key} style={{ textAlign: 'center' }}>
                      <PermCell value={(r.permissions as any)[c.key]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Role descriptions */}
        <div className="grid grid-cols-2 gap-4">
          {ROLES.map(r => (
            <div key={r.key} className="card">
              <div className="text-[13px] font-medium mb-1">{r.role}</div>
              <div className="text-[11.5px] text-ink/50 mb-3">{r.desc}</div>
              <div className="space-y-1.5">
                {COLS.filter(c => (r.permissions as any)[c.key]).map(c => (
                  <div key={c.key} className="flex items-center gap-2 text-[11.5px] text-ink/70">
                    <CheckCircle size={11} className="text-brand-green flex-shrink-0" />
                    {c.label}
                    {(r.permissions as any)[c.key] !== true && (
                      <span className="tag tag-amber text-[9px] ml-1">{String((r.permissions as any)[c.key])}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* API key note */}
        <div className="card mt-4" style={{ background: '#F0EEE9', border: 'none' }}>
          <div className="text-[12px] font-medium mb-1.5">API access and programmatic roles</div>
          <div className="text-[11.5px] text-ink/60 leading-relaxed">
            All API endpoints enforce role checks via JWT claims. The role is embedded in the access token at login and validated on every request.
            Operators can view the full audit log to see every action taken across all roles.
            Role upgrades or reassignments require Super Admin access and are logged to the audit trail.
          </div>
        </div>
      </div>
    </AppShell>
  )
}
