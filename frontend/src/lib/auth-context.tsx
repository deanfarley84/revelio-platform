'use client'
import React, { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '@/lib/api'

interface User {
  id: string; email: string; full_name: string; role: string; org_id: string | null
}

interface AuthCtx {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAdmin: boolean
  isOperator: boolean
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    const t = localStorage.getItem('vyre_token')
    const u = localStorage.getItem('vyre_user')
    if (t && u) { setToken(t); setUser(JSON.parse(u)) }
  }, [])

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    const { access_token, user: u } = res.data
    localStorage.setItem('vyre_token', access_token)
    localStorage.setItem('vyre_user', JSON.stringify(u))
    setToken(access_token); setUser(u)
  }

  const logout = () => {
    localStorage.removeItem('vyre_token'); localStorage.removeItem('vyre_user')
    setToken(null); setUser(null)
    window.location.href = '/auth/login'
  }

  const adminRoles = ['super_admin', 'operator_admin']
  const operatorRoles = ['super_admin', 'operator_admin', 'analyst']

  return (
    <AuthContext.Provider value={{
      user, token,
      login, logout,
      isAdmin: adminRoles.includes(user?.role || ''),
      isOperator: operatorRoles.includes(user?.role || ''),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
