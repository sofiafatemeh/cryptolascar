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
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-xs">
        <div className="text-center mb-12">
          <h1 className="font-display text-5xl tracking-[0.2em] text-or-lascar uppercase mb-2">
            Crypto<br />Lascar
          </h1>
          <p className="text-xs text-blanc-linen/30 tracking-widest uppercase">
            La rue enseigne, le marché récompense.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="border border-or-sale/30 bg-anthracite rounded px-4 py-3 focus-within:border-or-lascar/50 transition-colors">
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
            className="w-full py-3 bg-or-lascar text-noir-bitume font-bold uppercase tracking-[0.2em] text-xs rounded hover:bg-or-sale transition-colors disabled:opacity-40"
          >
            {loading ? '...' : 'Entrer'}
          </button>
        </form>
      </div>
    </div>
  )
}
