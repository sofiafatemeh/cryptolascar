'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const links = [
  { href: '/dashboard', label: 'Daily' },
  { href: '/dashboard/weekly', label: 'Weekly' },
  { href: '/dashboard/monthly', label: 'Monthly' },
]

export default function Navigation() {
  const pathname = usePathname()

  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' })
    window.location.href = '/login'
  }

  return (
    <header className="border-b border-or-sale/20 bg-anthracite/95 sticky top-0 z-10 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto px-4 h-13 flex items-center justify-between py-2">
        <div className="flex items-center gap-6">
          {/* Brand mark */}
          <Link href="/dashboard" className="flex items-center gap-2 group">
            <span className="text-or-lascar text-lg leading-none select-none" style={{ fontFamily: 'serif' }}>☠</span>
            <div className="flex flex-col leading-none">
              <span className="font-brush text-or-lascar text-xs tracking-wide">CRYPTO</span>
              <span className="font-display text-blanc-linen text-xs tracking-[0.25em] uppercase">LASCAR</span>
            </div>
          </Link>

          <nav className="flex gap-5">
            {links.map(l => (
              <Link
                key={l.href}
                href={l.href}
                className={`text-xs uppercase tracking-widest transition-colors ${
                  pathname === l.href
                    ? 'text-or-lascar'
                    : 'text-blanc-linen/30 hover:text-blanc-linen/70'
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <button
          onClick={logout}
          className="text-xs text-blanc-linen/20 hover:text-blanc-linen/50 transition-colors uppercase tracking-widest"
        >
          ↩
        </button>
      </div>
    </header>
  )
}
