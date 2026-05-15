import { NextResponse } from 'next/server'
import { saveReport } from '@/lib/blob'

export async function POST(request: Request) {
  const apiKey = request.headers.get('x-api-key')
  if (!apiKey || apiKey !== process.env.INGEST_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const { type, date, content_md, content_html, metadata } = body as Record<string, unknown>

  if (!type || !date || !content_md) {
    return NextResponse.json({ error: 'Missing: type, date, content_md' }, { status: 400 })
  }

  await saveReport({
    type: type as 'daily' | 'weekly' | 'monthly',
    date: date as string,
    content_md: content_md as string,
    content_html: content_html as string | undefined,
    metadata: metadata as Record<string, unknown> | undefined,
  })

  return NextResponse.json({ ok: true, stored: `reports/${type}/${date}.json` })
}
