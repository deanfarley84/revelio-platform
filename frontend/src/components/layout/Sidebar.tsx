'use client'
import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import {
  LayoutGrid, Upload, FileText, BarChart2, Settings,
  CheckSquare, Users, TrendingUp, Sliders, Eye, GitBranch, Lock, BrainCircuit, Calculator
} from 'lucide-react'

interface NavItem { href: string; label: string; icon: React.ReactNode; badge?: string | number; badgeVariant?: 'alert' | 'default' }

const clientNav: NavItem[] = [
  { href: '/dashboard', label: 'Overview', icon: <LayoutGrid size={13} /> },
  { href: '/submit', label: 'Upload & analyse', icon: <Upload size={13} />, badge: 'New', badgeVariant: 'alert' },
  { href: '/submit/manual', label: 'Manual entry', icon: <FileText size={13} /> },
  { href: '/results', label: 'My results', icon: <BarChart2 size={13} /> },
  { href: '/roi', label: 'ROI calculator', icon: <Calculator size={13} /> },
  { href: '/reports', label: 'Reports', icon: <FileText size={13} /> },
]

const adminNav: NavItem[] = [
  { href: '/admin', label: 'Command centre', icon: <LayoutGrid size={13} /> },
  { href: '/admin/queue', label: 'Approval queue', icon: <CheckSquare size={13} />, badge: 3, badgeVariant: 'alert' },
  { href: '/admin/intel', label: 'Client intelligence', icon: <BrainCircuit size={13} /> },
  { href: '/admin/clients', label: 'All clients', icon: <Users size={13} /> },
  { href: '/admin/benchmarks', label: 'Benchmarks', icon: <Sliders size={13} /> },
  { href: '/admin/ai-review', label: 'AI review', icon: <Eye size={13} /> },
  { href: '/admin/pipeline', label: 'Pipeline', icon: <GitBranch size={13} /> },
  { href: '/admin/roles', label: 'Roles', icon: <Lock size={13} /> },
]

export default function Sidebar() {
  const { user, logout, isOperator } = useAuth()
  const pathname = usePathname()
  const isAdminPath = pathname?.startsWith('/admin')
  const nav = isAdminPath ? adminNav : clientNav
  const initials = user?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'

  return (
    <aside className="w-52 min-w-52 flex flex-col" style={{ background: '#1A1830', minHeight: '100vh' }}>
      {/* Logo */}
      <div className="px-4 py-[18px] border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-[7px] flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.1)' }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5">
              <polygon points="7,1 13,4.5 13,9.5 7,13 1,9.5 1,4.5"/>
              <line x1="7" y1="1" x2="7" y2="13"/><line x1="1" y1="4.5" x2="13" y2="9.5"/><line x1="13" y1="4.5" x2="1" y2="9.5"/>
            </svg>
          </div>
          <div>
            <div className="text-[13px] font-semibold text-white/90">REVION</div>
            <div className="text-[9.5px] text-white/30 uppercase tracking-widest">Revenue Diagnostics</div>
          </div>
        </div>
      </div>

      {/* Mode toggle for operators */}
      {isOperator && (
        <div className="px-3 pt-2.5">
          <div className="flex rounded-md p-0.5" style={{ background: 'rgba(0,0,0,0.25)' }}>
            <Link href="/dashboard" className={`flex-1 text-center py-1.5 rounded text-[10.5px] font-medium transition-all ${!isAdminPath ? 'text-white/88' : 'text-white/35'}`}
              style={{ background: !isAdminPath ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
              Client
            </Link>
            <Link href="/admin" className={`flex-1 text-center py-1.5 rounded text-[10.5px] font-medium transition-all ${isAdminPath ? 'text-white/88' : 'text-white/35'}`}
              style={{ background: isAdminPath ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
              Admin
            </Link>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="px-2.5 pt-2 flex-1">
        {isAdminPath && (
          <>
            <div className="text-[9px] text-white/28 uppercase tracking-widest px-2 mb-1.5 mt-1 font-medium">Intelligence</div>
            {adminNav.slice(0, 4).map(item => <NavLink key={item.href} item={item} pathname={pathname} />)}
            <div className="h-px my-2 mx-2" style={{ background: 'rgba(255,255,255,0.06)' }} />
            <div className="text-[9px] text-white/28 uppercase tracking-widest px-2 mb-1.5 font-medium">Configuration</div>
            {adminNav.slice(4).map(item => <NavLink key={item.href} item={item} pathname={pathname} />)}
          </>
        )}
        {!isAdminPath && (
          <>
            <div className="text-[9px] text-white/28 uppercase tracking-widest px-2 mb-1.5 mt-1 font-medium">Workspace</div>
            {clientNav.map(item => <NavLink key={item.href} item={item} pathname={pathname} />)}
          </>
        )}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-white/[0.06]">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:bg-white/[0.06] transition-colors" onClick={logout}>
          <div className="w-6.5 h-6.5 rounded-full flex items-center justify-center text-[10px] font-semibold text-white/75"
            style={{ background: 'rgba(255,255,255,0.13)', width: 26, height: 26 }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[11.5px] font-medium text-white/75 truncate">{user?.full_name}</div>
            <div className="text-[9.5px] text-white/30 capitalize">{user?.role?.replace('_', ' ')}</div>
          </div>
        </div>
      </div>
    </aside>
  )
}

function NavLink({ item, pathname }: { item: NavItem; pathname: string | null }) {
  const active = pathname === item.href || (item.href !== '/admin' && item.href !== '/dashboard' && pathname?.startsWith(item.href))
  return (
    <Link href={item.href}
      className={`flex items-center gap-2 px-2 py-[7px] rounded-md text-[12px] mb-0.5 transition-all ${active ? 'font-medium' : 'font-normal'}`}
      style={{
        color: active ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.48)',
        background: active ? 'rgba(255,255,255,0.1)' : 'transparent',
      }}>
      {item.icon}
      <span className="flex-1">{item.label}</span>
      {item.badge != null && (
        <span className={`text-[9.5px] px-1.5 py-0.5 rounded-full font-mono ${item.badgeVariant === 'alert' ? 'bg-red-600 text-white' : 'text-white/60'}`}
          style={item.badgeVariant !== 'alert' ? { background: 'rgba(255,255,255,0.12)' } : {}}>
          {item.badge}
        </span>
      )}
    </Link>
  )
}
