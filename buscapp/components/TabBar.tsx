'use client'
import Link from 'next/link'

export type ActiveTab = 'camera' | 'upload' | 'auto' | 'fashion'

const TABS: { id: ActiveTab; icon: string; label: string; href: string }[] = [
  { id: 'camera',  icon: '📷', label: 'Câmera', href: '/' },
  { id: 'upload',  icon: '🖼️', label: 'Upload',  href: '/upload' },
  { id: 'auto',    icon: '🚗', label: 'Auto',    href: '/auto' },
  { id: 'fashion', icon: '👗', label: 'Moda',    href: '/fashion' },
]

interface TabBarProps {
  active: ActiveTab
}

export function TabBar({ active }: TabBarProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-background border-t border-border flex h-16 z-50">
      {TABS.map(tab => (
        <Link
          key={tab.id}
          href={tab.href}
          className={`flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors active:opacity-70 ${
            active === tab.id ? 'text-primary' : 'text-text-secondary'
          }`}
        >
          <span className="text-xl leading-none">{tab.icon}</span>
          <span className={`text-[10px] ${active === tab.id ? 'font-semibold' : ''}`}>
            {tab.label}
          </span>
        </Link>
      ))}
    </nav>
  )
}
