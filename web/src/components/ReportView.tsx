import type { Report } from '@/lib/blob'

interface Section {
  title: string
  body: string
}

function parseMarkdownSections(md: string): Section[] {
  const parts = md.split(/^## /m).filter(Boolean)
  return parts.map(part => {
    const newline = part.indexOf('\n')
    const title = newline === -1 ? part.trim() : part.slice(0, newline).trim()
    const body = newline === -1 ? '' : part.slice(newline + 1).trim()
    return { title, body }
  })
}

function sectionIcon(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('macro')) return '◈'
  if (t.includes('etf')) return '▣'
  if (t.includes('crypto')) return '◉'
  if (t.includes('pea')) return '◧'
  if (t.includes('news') || t.includes('actu')) return '◌'
  if (t.includes('synthèse') || t.includes('synthese') || t.includes('résumé')) return '☠'
  return '◆'
}

// Color-code financial percentages: green if positive, red if negative
function colorizeNumbers(text: string): string {
  return text.replace(/([+\-]?\d+(?:[.,]\d+)?)\s*%/g, (match, num) => {
    const val = parseFloat(num.replace(',', '.'))
    if (val > 0) return `<span class="val-positive font-semibold">${match}</span>`
    if (val < 0) return `<span class="val-negative font-semibold">${match}</span>`
    return match
  })
}

function inlineFormat(text: string): string {
  return colorizeNumbers(
    text
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-blanc-linen font-semibold">$1</strong>')
      .replace(/\*(.+?)\*/g, '<em class="text-blanc-linen/60">$1</em>')
      .replace(/`(.+?)`/g, '<code class="text-or-lascar/80 bg-noir-bitume px-1 rounded text-xs">$1</code>')
  )
}

function MarkdownBody({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-2" />
        if (line.startsWith('### ')) {
          return (
            <p key={i} className="text-xs uppercase tracking-widest text-or-sale/70 mt-4 mb-1 font-display">
              {line.replace('### ', '')}
            </p>
          )
        }
        if (line.startsWith('> ')) {
          return (
            <p key={i} className="border-l-2 border-or-lascar/30 pl-3 text-xs text-blanc-linen/50 italic">
              {line.replace('> ', '')}
            </p>
          )
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <p key={i} className="text-sm text-blanc-linen/70 flex gap-2">
              <span className="text-or-lascar/60 text-xs mt-0.5 shrink-0">▸</span>
              <span dangerouslySetInnerHTML={{ __html: inlineFormat(line.slice(2)) }} />
            </p>
          )
        }
        return (
          <p key={i} className="text-sm text-blanc-linen/75 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: inlineFormat(line) }}
          />
        )
      })}
    </div>
  )
}

export default function ReportView({ report }: { report: Report }) {
  const sections = parseMarkdownSections(report.content_md)

  return (
    <div className="space-y-3">
      {sections.map((section, i) => (
        <div
          key={i}
          className="relative bg-anthracite border border-or-sale/15 rounded-lg p-5 hover:border-or-sale/35 transition-colors overflow-hidden card-grain"
        >
          {/* Subtle X watermark on first card */}
          {i === 0 && (
            <span className="absolute -right-4 -bottom-6 text-blanc-linen/[0.03] font-display select-none pointer-events-none" style={{ fontSize: '7rem', lineHeight: 1 }}>✕</span>
          )}

          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-or-sale/15">
              <span className="text-or-lascar/70 text-sm">{sectionIcon(section.title)}</span>
              <h2 className="font-display text-sm uppercase tracking-[0.2em] text-or-lascar">
                {section.title}
              </h2>
            </div>
            {section.body ? (
              <MarkdownBody text={section.body} />
            ) : (
              <p className="text-xs text-blanc-linen/25 italic">Aucune donnée disponible.</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
