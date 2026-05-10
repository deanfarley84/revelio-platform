'use client'
import React, { useEffect, useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { authApi } from '@/lib/api'
import { Settings, Check, AlertCircle } from 'lucide-react'

type Banner = { tone: 'ok' | 'error'; text: string } | null

export default function SettingsPage() {
  const [me, setMe] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const [profileBusy, setProfileBusy] = useState(false)
  const [profileBanner, setProfileBanner] = useState<Banner>(null)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')

  const [pwBusy, setPwBusy] = useState(false)
  const [pwBanner, setPwBanner] = useState<Banner>(null)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  useEffect(() => {
    authApi.me()
      .then(r => {
        setMe(r.data)
        setFullName(r.data.full_name || '')
        setEmail(r.data.email || '')
      })
      .finally(() => setLoading(false))
  }, [])

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (profileBusy) return
    setProfileBusy(true)
    setProfileBanner(null)
    try {
      const payload: any = {}
      if (fullName.trim() && fullName.trim() !== me?.full_name) payload.full_name = fullName.trim()
      if (email.trim() && email.trim().toLowerCase() !== me?.email) payload.email = email.trim().toLowerCase()
      if (Object.keys(payload).length === 0) {
        setProfileBanner({ tone: 'ok', text: 'Nothing to update.' })
      } else {
        const res = await authApi.updateMe(payload)
        setMe(res.data.user)
        setProfileBanner({ tone: 'ok', text: `Saved: ${res.data.changed.join(', ') || 'no changes'}` })
      }
    } catch (err: any) {
      setProfileBanner({ tone: 'error', text: err?.response?.data?.detail || 'Could not save profile.' })
    } finally {
      setProfileBusy(false)
    }
  }

  const savePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (pwBusy) return
    if (newPassword !== confirmPassword) {
      setPwBanner({ tone: 'error', text: 'New password and confirmation do not match.' })
      return
    }
    if (newPassword.length < 8) {
      setPwBanner({ tone: 'error', text: 'New password must be at least 8 characters.' })
      return
    }
    setPwBusy(true)
    setPwBanner(null)
    try {
      await authApi.updateMe({ current_password: currentPassword, new_password: newPassword })
      setPwBanner({ tone: 'ok', text: 'Password updated.' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setPwBanner({ tone: 'error', text: err?.response?.data?.detail || 'Could not change password.' })
    } finally {
      setPwBusy(false)
    }
  }

  return (
    <AppShell>
      <div className="max-w-3xl">
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="section-title flex items-center gap-2">
              <Settings size={16} className="text-ink/70" />
              Settings
            </div>
            <div className="section-sub">Update your profile and password</div>
          </div>
        </div>

        {loading ? (
          <div className="card text-[12px] text-ink/40">Loading...</div>
        ) : (
          <>
            <div className="card mb-4">
              <div className="kpi-label mb-3">Profile</div>
              <form onSubmit={saveProfile} className="form-grid-2">
                <div>
                  <label className="label">Full name</label>
                  <input className="input" value={fullName} onChange={e => setFullName(e.target.value)} />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input className="input" value={email} onChange={e => setEmail(e.target.value)} type="email" />
                </div>
                <div>
                  <label className="label">Role</label>
                  <input className="input" value={me?.role || ''} disabled />
                </div>
                <div className="flex items-end">
                  <button type="submit" disabled={profileBusy} className="btn-primary btn-sm">
                    {profileBusy ? 'Saving...' : 'Save profile'}
                  </button>
                </div>
              </form>
              {profileBanner && (
                <div className={`mt-3 text-[12px] flex items-center gap-1.5 ${profileBanner.tone === 'ok' ? 'text-brand-green' : 'text-brand-red'}`}>
                  {profileBanner.tone === 'ok' ? <Check size={13}/> : <AlertCircle size={13}/>}
                  {profileBanner.text}
                </div>
              )}
            </div>

            <div className="card">
              <div className="kpi-label mb-3">Change password</div>
              <form onSubmit={savePassword} className="form-grid-2">
                <div className="col-span-2">
                  <label className="label">Current password</label>
                  <input className="input" type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} autoComplete="current-password" />
                </div>
                <div>
                  <label className="label">New password</label>
                  <input className="input" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} autoComplete="new-password" />
                </div>
                <div>
                  <label className="label">Confirm new password</label>
                  <input className="input" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} autoComplete="new-password" />
                </div>
                <div className="col-span-2 flex justify-end">
                  <button type="submit" disabled={pwBusy} className="btn-primary btn-sm">
                    {pwBusy ? 'Saving...' : 'Update password'}
                  </button>
                </div>
              </form>
              {pwBanner && (
                <div className={`mt-3 text-[12px] flex items-center gap-1.5 ${pwBanner.tone === 'ok' ? 'text-brand-green' : 'text-brand-red'}`}>
                  {pwBanner.tone === 'ok' ? <Check size={13}/> : <AlertCircle size={13}/>}
                  {pwBanner.text}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}
