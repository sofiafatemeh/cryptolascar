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
    access: 'private' as unknown as 'public',
    contentType: 'application/json',
    addRandomSuffix: false,
  })
}

export async function getLatestReport(type: ReportType): Promise<Report | null> {
  if (!process.env.BLOB_READ_WRITE_TOKEN) return null
  try {
    const { blobs } = await list({ prefix: `reports/${type}/` })
    if (!blobs.length) return null
    const sorted = blobs.sort((a, b) => b.pathname.localeCompare(a.pathname))
    const res = await fetch(sorted[0].url, { next: { revalidate: 60 } })
    return res.json()
  } catch {
    return null
  }
}

export async function getReport(type: ReportType, date: string): Promise<Report | null> {
  if (!process.env.BLOB_READ_WRITE_TOKEN) return null
  try {
    const { blobs } = await list({ prefix: `reports/${type}/${date}` })
    if (!blobs.length) return null
    const res = await fetch(blobs[0].url)
    return res.json()
  } catch {
    return null
  }
}

export async function listReports(type: ReportType): Promise<{ date: string; url: string }[]> {
  if (!process.env.BLOB_READ_WRITE_TOKEN) return []
  try {
    const { blobs } = await list({ prefix: `reports/${type}/` })
    return blobs
      .sort((a, b) => b.pathname.localeCompare(a.pathname))
      .map(b => ({
        date: b.pathname.replace(`reports/${type}/`, '').replace('.json', ''),
        url: b.url,
      }))
  } catch {
    return []
  }
}
