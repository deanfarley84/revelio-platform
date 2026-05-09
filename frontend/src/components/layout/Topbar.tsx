'use client'
import React, { useState, useEffect } from 'react'
import { Bell } from 'lucide-react'
import { notificationsApi } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export default function Topbar() {
  const { user } = useAuth()
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    notificationsApi.list().then(r => {
      setUnread(r.data.filter((n: any) => !n.read).length)
    }).catch(() => {})
  }, [])

  return (
    <header className="h-[50px] bg-white border-b border-black/[0.07] flex items-center px-6 gap-4 flex-shrink-0 sticky top-0 z-20">
      <div className="flex-1" />
      <div className="flex items-center gap-1.5 bg-surface-2 border border-black/[0.07] rounded-full px-3 py-1.5 text-[10.5px] text-ink/50 font-medium">
        <div className="w-2 h-2 rounded-full bg-brand-blue" />
        Claude AI engine active
      </div>
      <button className="relative p-2 rounded-lg hover:bg-surface-2 text-ink/50 transition-colors">
        <Bell size={15} />
        {unread > 0 && (
          <span className="absolute top-1 right-1 w-3.5 h-3.5 bg-red-500 rounded-full text-white text-[8px] flex items-center justify-center font-bold">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
    </header>
  )
}
