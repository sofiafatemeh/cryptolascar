import type { Metadata } from 'next'
import { Anton, Permanent_Marker } from 'next/font/google'
import './globals.css'

const anton = Anton({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-anton',
  display: 'swap',
})

const permanentMarker = Permanent_Marker({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-brush',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Crypto Lascar',
  description: 'Discret dans la rue, précis sur les chiffres.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${anton.variable} ${permanentMarker.variable}`}>
      <body className="bg-noir-bitume text-blanc-linen min-h-screen font-body antialiased">
        {children}
      </body>
    </html>
  )
}
