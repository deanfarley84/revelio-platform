'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

export default function RootPage() {
  const { user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!user) {
      router.push('/auth/login')
    } else {
      const isAdmin = ['super_admin', 'operator_admin', 'analyst'].includes(user.role)
      router.push(isAdmin ? '/admin' : '/dashboard')
    }
  }, [user])

  return (
    <div style={{ minHeight: '100vh', background: '#F5F4F1', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontFamily: 'DM Sans, sans-serif' }}>
        <div style={{ width: '28px', height: '28px', background: '#1A1830', borderRadius: '7px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="rgba(255,255,255,0.9)" strokeWidth="1.5">
            <polygon points="7,1 13,4.5 13,9.5 7,13 1,9.5 1,4.5"/>
          </svg>
        </div>
        <span style={{ fontSize: '14px', color: '#95928A' }}>Loading VYRE...</span>
      </div>
    </div>
  )
}
