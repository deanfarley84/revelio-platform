'use client'
import React, { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { invitationsApi } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export default function InviteAcceptPage() {
  const params = useParams<{ token: string }>()
  const router = useRouter()
  const { setSession } = useAuth() as any
  const token = params.token

  const [preview, setPreview] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    invitationsApi.preview(token)
      .then(r => setPreview(r.data))
      .catch(err => setLoadError(err?.response?.data?.detail || 'Invitation not found.'))
      .finally(() => setLoading(false))
  }, [token])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (busy) return
    if (password !== confirm) {
      setSubmitError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setSubmitError('Password must be at least 8 characters.')
      return
    }
    setBusy(true)
    setSubmitError(null)
    try {
      const res = await invitationsApi.accept(token, { full_name: fullName.trim(), password })
      const { access_token, user } = res.data
      // Mirror what login flow does: persist token + user, redirect to dashboard.
      if (typeof window !== 'undefined') {
        localStorage.setItem('vyre_token', access_token)
        localStorage.setItem('vyre_user', JSON.stringify(user))
      }
      if (typeof setSession === 'function') setSession({ token: access_token, user })
      router.replace('/dashboard')
    } catch (err: any) {
      setSubmitError(err?.response?.data?.detail || 'Could not accept invitation.')
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#FAF9F5', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ maxWidth: 460, width: '100%', background: 'white', borderRadius: 12, padding: 32, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
        <div style={{ marginBottom: 18 }}>
          <span style={{ fontSize: 18, fontWeight: 600, color: '#1A1830', fontFamily: 'DM Sans, sans-serif' }}>OUTTURN</span>
          <p style={{ fontSize: 12, color: '#95928A', letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'DM Sans, sans-serif', marginTop: 4 }}>Revenue Leakage Diagnostics</p>
        </div>

        {loading ? (
          <p className="text-[12px] text-ink/40">Loading invitation…</p>
        ) : loadError ? (
          <div>
            <h1 className="text-[18px] font-semibold mb-2">Invitation unavailable</h1>
            <p className="text-[12.5px] text-ink/65">{loadError}</p>
          </div>
        ) : (
          <>
            <h1 className="text-[18px] font-semibold mb-1">Join {preview?.org_name || 'your team'}</h1>
            <p className="text-[12.5px] text-ink/65 mb-4">
              You have been invited as {preview?.role?.replace('_', ' ') || 'team member'}. Set a password to activate the account for <strong>{preview?.email}</strong>.
            </p>
            <form onSubmit={onSubmit} className="space-y-3">
              <div>
                <label className="label">Full name</label>
                <input className="input" value={fullName} onChange={e => setFullName(e.target.value)} required autoFocus />
              </div>
              <div>
                <label className="label">Password</label>
                <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" required />
              </div>
              <div>
                <label className="label">Confirm password</label>
                <input className="input" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} autoComplete="new-password" required />
              </div>
              {submitError && (
                <div className="text-[12px] text-brand-red">{submitError}</div>
              )}
              <button type="submit" disabled={busy} className="btn-primary btn-sm w-full">
                {busy ? 'Activating…' : 'Activate account'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
