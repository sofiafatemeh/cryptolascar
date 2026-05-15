import Image from 'next/image'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-noir-bitume flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Background X motif */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
        <span
          className="text-blanc-linen font-display opacity-[0.02]"
          style={{ fontSize: '90vw', lineHeight: 1 }}
        >
          ✕
        </span>
      </div>

      {/* Radial glow behind logo */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[500px] h-[500px] rounded-full bg-or-lascar opacity-[0.04] blur-[80px]" />
      </div>

      <div className="relative z-10 flex flex-col items-center">
        {/* Logo */}
        <div className="w-72 h-72 sm:w-96 sm:h-96 relative mb-10 drop-shadow-2xl">
          <Image
            src="/logo.png"
            alt="Crypto Lascar"
            fill
            className="object-contain"
            priority
          />
        </div>

        {/* CTA */}
        <Link
          href="/dashboard"
          className="group relative px-10 py-4 border border-or-lascar/60 text-or-lascar font-display uppercase tracking-[0.35em] text-sm hover:bg-or-lascar hover:text-noir-bitume transition-all duration-300"
        >
          <span className="relative z-10">Entrer</span>
          {/* Gold shimmer on hover */}
          <div className="absolute inset-0 bg-or-lascar opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </Link>

        <p className="mt-6 text-blanc-linen/20 text-xs tracking-[0.2em] uppercase">
          Discret dans la rue, précis sur les chiffres.
        </p>
      </div>
    </div>
  )
}
