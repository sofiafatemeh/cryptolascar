'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })

    if (res.ok) {
      router.push('/dashboard')
    } else {
      setError('Mot de passe incorrect.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background X motif */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
        <span className="text-blanc-linen opacity-[0.025] font-display" style={{ fontSize: '40vw', lineHeight: 1 }}>✕</span>
      </div>

      <div className="w-full max-w-xs relative z-10">
        {/* Skull icon */}
        <div className="text-center mb-2">
          <span
            className="text-or-lascar block leading-none select-none"
            style={{ fontSize: '4rem', fontFamily: 'serif', filter: 'drop-shadow(0 0 12px rgba(245,197,66,0.3))' }}
          >
            ☠
          </span>
        </div>

        {/* Wordmark */}
        <div className="text-center mb-10">
          <div className="leading-none mb-1">
            <span className="font-brush text-or-lascar block" style={{ fontSize: '2.8rem', lineHeight: 1, filter: 'drop-shadow(0 0 8px rgba(245,197,66,0.25))' }}>
              CRYPTO
            </span>
            <span className="font-display text-blanc-linen block tracking-[0.3em] uppercase" style={{ fontSize: '2.2rem', lineHeight: 1 }}>
              LASCAR
            </span>
          </div>
          <div className="flex items-center justify-center gap-2 mt-4">
            <span className="h-px w-8 bg-or-sale/40" />
            <p className="text-xs text-blanc-linen/30 tracking-widest uppercase">
              Bons plans. Marchés. Rue.
            </p>
            <span className="h-px w-8 bg-or-sale/40" />
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="border border-or-sale/30 bg-anthracite rounded px-4 py-3 focus-within:border-or-lascar/60 transition-colors">
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-transparent text-blanc-linen placeholder-blanc-linen/20 outline-none text-sm tracking-widest"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-red-400/80 text-xs text-center tracking-wide">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-3 bg-or-lascar text-noir-bitume font-display uppercase tracking-[0.3em] text-sm rounded hover:bg-or-sale transition-colors disabled:opacity-40"
          >
            {loading ? '...' : 'Entrer'}
          </button>
        </form>

        <p className="text-center text-blanc-linen/15 text-xs mt-8 tracking-widest uppercase">
          Discret dans la rue, précis sur les chiffres.
        </p>
      </div>
    </div>
  )
}
