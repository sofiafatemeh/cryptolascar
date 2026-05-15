import { getReport } from '@/lib/blob'
import Navigation from '@/components/Navigation'
import ReportView from '@/components/ReportView'
import Link from 'next/link'
import type { ReportType } from '@/lib/blob'

export const dynamic = 'force-dynamic'

interface Props {
  searchParams: Promise<{ type?: string; date?: string }>
}

export default async function ReportPage({ searchParams }: Props) {
  const { type, date } = await searchParams
  const reportType = (type as ReportType) || 'daily'
  const backHref = `/dashboard${reportType !== 'daily' ? `/${reportType}` : ''}`

  const report = date ? await getReport(reportType, date) : null

  return (
    <div className="min-h-screen">
      <Navigation />
      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-baseline justify-between mb-7 pb-5 border-b border-or-sale/20">
          <div className="flex items-center gap-3">
            <Link
              href={backHref}
              className="text-blanc-linen/25 hover:text-blanc-linen/60 text-xs transition-colors"
            >
              ← {reportType}
            </Link>
            <h1 className="font-display text-2xl text-or-lascar uppercase tracking-[0.2em]">
              {date}
            </h1>
          </div>
        </div>

        {!report ? (
          <div className="text-center py-24">
            <p className="text-blanc-linen/30 text-sm">Rapport introuvable.</p>
          </div>
        ) : (
          <ReportView report={report} />
        )}
      </main>
    </div>
  )
}
