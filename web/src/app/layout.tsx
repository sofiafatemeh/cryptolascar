import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Crypto Lascar',
  description: 'Discret dans la rue, précis sur les chiffres.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-noir-bitume text-blanc-linen min-h-screen font-body antialiased">
        {children}
      </body>
    </html>
  )
}
