import { put, list } from '@vercel/blob'

export type ReportType = 'daily' | 'weekly' | 'monthly'

export interface Report {
  type: ReportType
  date: string
  content_md: string
  content_html?: string
  metadata?: Record<string, unknown>
}

export async function saveReport(report: Report): Promise<void> {
  const pathname = `reports/${report.type}/${report.date}.json`
  await put(pathname, JSON.stringify(report), {
    access: 'public',
    contentType: 'application/json',
    addRandomSuffix: false,
  })
}

export async function getLatestReport(type: ReportType): Promise<Report | null> {
  const { blobs } = await list({ prefix: `reports/${type}/` })
  if (!blobs.length) return null
  const sorted = blobs.sort((a, b) => b.pathname.localeCompare(a.pathname))
  const res = await fetch(sorted[0].url, { next: { revalidate: 60 } })
  return res.json()
}

export async function getReport(type: ReportType, date: string): Promise<Report | null> {
  const { blobs } = await list({ prefix: `reports/${type}/${date}` })
  if (!blobs.length) return null
  const res = await fetch(blobs[0].url)
  return res.json()
}

export async function listReports(type: ReportType): Promise<{ date: string; url: string }[]> {
  const { blobs } = await list({ prefix: `reports/${type}/` })
  return blobs
    .sort((a, b) => b.pathname.localeCompare(a.pathname))
    .map(b => ({
      date: b.pathname.replace(`reports/${type}/`, '').replace('.json', ''),
      url: b.url,
    }))
}
