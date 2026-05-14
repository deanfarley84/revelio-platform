'use client'
import React, { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const { login, user } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (user) {
      const isAdmin = ['super_admin','operator_admin','analyst'].includes(user.role)
      router.push(isAdmin ? '/admin' : '/dashboard')
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    }
    setLoading(false)
  }

  return (
    <div style={{ minHeight:'100vh', background:'#F5F4F1', display:'flex', alignItems:'center', justifyContent:'center', padding:'24px' }}>
      <div style={{ width:'100%', maxWidth:'400px' }}>
        {/* Logo */}
        <div style={{ textAlign:'center', marginBottom:'32px' }}>
          <div style={{ display:'inline-flex', alignItems:'center', gap:'10px', marginBottom:'8px' }}>
            <div style={{ width:'32px', height:'32px', background:'#1A1830', borderRadius:'8px', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <svg width="16" height="16" viewBox="0 0 14 14" fill="none" stroke="rgba(255,255,255,0.9)" strokeWidth="1.5">
                <polygon points="7,1 13,4.5 13,9.5 7,13 1,9.5 1,4.5"/>
                <line x1="7" y1="1" x2="7" y2="13"/>
                <line x1="1" y1="4.5" x2="13" y2="9.5"/>
                <line x1="13" y1="4.5" x2="1" y2="9.5"/>
              </svg>
            </div>
            <span style={{ fontSize:'18px', fontWeight:600, color:'#1A1830', fontFamily:'DM Sans, sans-serif' }}>VYRE</span>
          </div>
          <p style={{ fontSize:'12px', color:'#95928A', letterSpacing:'0.06em', textTransform:'uppercase', fontFamily:'DM Sans, sans-serif' }}>Revenue Leakage Diagnostics</p>
        </div>

        {/* Card */}
        <div style={{ background:'white', borderRadius:'12px', border:'1px solid rgba(0,0,0,0.07)', padding:'32px' }}>
          <h1 style={{ fontSize:'18px', fontWeight:500, color:'#0D0C0A', marginBottom:'6px', fontFamily:'DM Sans, sans-serif' }}>Sign in</h1>
          <p style={{ fontSize:'12.5px', color:'#95928A', marginBottom:'24px', fontFamily:'DM Sans, sans-serif' }}>Enter your credentials to access your workspace</p>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom:'14px' }}>
              <label style={{ display:'block', fontSize:'11.5px', fontWeight:500, color:'rgba(13,12,10,0.6)', marginBottom:'6px', fontFamily:'DM Sans, sans-serif' }}>Email address</label>
              <input
                type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                style={{ width:'100%', border:'1px solid rgba(0,0,0,0.13)', borderRadius:'8px', padding:'9px 12px', fontSize:'13px', color:'#0D0C0A', background:'white', outline:'none', fontFamily:'DM Sans, sans-serif', boxSizing:'border-box' }}
                onFocus={e => e.target.style.borderColor='#1B5DB5'}
                onBlur={e => e.target.style.borderColor='rgba(0,0,0,0.13)'}
              />
            </div>
            <div style={{ marginBottom:'20px' }}>
              <label style={{ display:'block', fontSize:'11.5px', fontWeight:500, color:'rgba(13,12,10,0.6)', marginBottom:'6px', fontFamily:'DM Sans, sans-serif' }}>Password</label>
              <input
                type="password" required value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                style={{ width:'100%', border:'1px solid rgba(0,0,0,0.13)', borderRadius:'8px', padding:'9px 12px', fontSize:'13px', color:'#0D0C0A', background:'white', outline:'none', fontFamily:'DM Sans, sans-serif', boxSizing:'border-box' }}
                onFocus={e => e.target.style.borderColor='#1B5DB5'}
                onBlur={e => e.target.style.borderColor='rgba(0,0,0,0.13)'}
              />
            </div>

            {error && (
              <div style={{ background:'#FBEAEA', border:'1px solid rgba(140,32,32,0.15)', borderRadius:'7px', padding:'10px 12px', marginBottom:'16px', fontSize:'12.5px', color:'#8C2020', fontFamily:'DM Sans, sans-serif' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading}
              style={{ width:'100%', background:'#1A1830', color:'white', border:'none', borderRadius:'8px', padding:'10px', fontSize:'13px', fontWeight:500, cursor:loading?'not-allowed':'pointer', opacity:loading?0.7:1, fontFamily:'DM Sans, sans-serif', transition:'background 0.15s' }}
              onMouseOver={e => { if(!loading)(e.target as HTMLButtonElement).style.background='#2D2B52' }}
              onMouseOut={e => { if(!loading)(e.target as HTMLButtonElement).style.background='#1A1830' }}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div style={{ marginTop:'20px', paddingTop:'20px', borderTop:'1px solid rgba(0,0,0,0.06)' }}>
            <p style={{ fontSize:'11.5px', color:'#95928A', textAlign:'center', fontFamily:'DM Sans, sans-serif' }}>
              Don't have an account?{' '}
              <a href="/auth/register" style={{ color:'#1B5DB5', textDecoration:'none' }}>Contact your administrator</a>
            </p>
          </div>
        </div>

        <p style={{ textAlign:'center', fontSize:'11px', color:'#95928A', marginTop:'20px', fontFamily:'DM Sans, sans-serif' }}>
          Payments Revenue Leakage Diagnostic Platform · Powered by Claude AI
        </p>
      </div>
    </div>
  )
}
