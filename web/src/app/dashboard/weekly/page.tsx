import { getLatestReport, listReports } from '@/lib/blob'
import Navigation from '@/components/Navigation'
import ReportView from '@/components/ReportView'
import Link from 'next/link'

export const dynamic = 'force-dynamic'

export default async function WeeklyPage() {
  const [report, archives] = await Promise.all([
    getLatestReport('weekly'),
    listReports('weekly'),
  ])

  return (
    <div className="min-h-screen">
      <Navigation />
      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-baseline justify-between mb-7 pb-5 border-b border-or-sale/20">
          <h1 className="font-display text-2xl text-or-lascar uppercase tracking-[0.2em]">
            Weekly
          </h1>
          {report && (
            <span className="text-blanc-linen/30 text-xs tracking-wide">
              Semaine du{' '}
              {new Date(report.date + 'T12:00:00').toLocaleDateString('fr-FR', {
                day: 'numeric', month: 'long',
              })}
            </span>
          )}
        </div>

        {!report ? (
          <div className="text-center py-24">
            <p className="text-4xl mb-4 opacity-20">◎</p>
            <p className="text-blanc-linen/30 text-sm">Aucun rapport weekly disponible.</p>
          </div>
        ) : (
          <ReportView report={report} />
        )}

        {archives.length > 1 && (
          <div className="mt-10 pt-6 border-t border-or-sale/15">
            <p className="text-xs uppercase tracking-widest text-blanc-linen/20 mb-3">Archives</p>
            <div className="flex flex-wrap gap-2">
              {archives.slice(1, 10).map(r => (
                <Link
                  key={r.date}
                  href={`/dashboard/report?type=weekly&date=${r.date}`}
                  className="text-xs px-2 py-1 border border-or-sale/15 rounded text-blanc-linen/35 hover:border-or-lascar/40 hover:text-or-lascar/70 transition-colors"
                >
                  {r.date}
                </Link>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
