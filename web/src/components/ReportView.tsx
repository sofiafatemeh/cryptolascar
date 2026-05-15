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

// Section icons by keyword
function sectionIcon(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('macro')) return '◈'
  if (t.includes('etf')) return '▣'
  if (t.includes('crypto')) return '◉'
  if (t.includes('pea')) return '◧'
  if (t.includes('news') || t.includes('actu')) return '◌'
  return '◆'
}

function MarkdownBody({ text }: { text: string }) {
  // Render body lines with basic inline formatting
  const lines = text.split('\n')
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-2" />
        if (line.startsWith('### ')) {
          return (
            <p key={i} className="text-xs uppercase tracking-widest text-blanc-linen/40 mt-3 mb-1">
              {line.replace('### ', '')}
            </p>
          )
        }
        if (line.startsWith('> ')) {
          return (
            <p key={i} className="border-l-2 border-or-sale/30 pl-3 text-xs text-blanc-linen/40 italic">
              {line.replace('> ', '')}
            </p>
          )
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <p key={i} className="text-sm text-blanc-linen/70 flex gap-2">
              <span className="text-or-lascar/50 text-xs mt-0.5 shrink-0">▸</span>
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

function inlineFormat(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-blanc-linen font-semibold">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em class="text-blanc-linen/60">$1</em>')
    .replace(/`(.+?)`/g, '<code class="text-or-lascar/80 bg-anthracite px-1 rounded text-xs">$1</code>')
}

export default function ReportView({ report }: { report: Report }) {
  const sections = parseMarkdownSections(report.content_md)

  return (
    <div className="space-y-3">
      {sections.map((section, i) => (
        <div
          key={i}
          className="bg-anthracite border border-or-sale/15 rounded-lg p-5 hover:border-or-sale/30 transition-colors"
        >
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-or-sale/15">
            <span className="text-or-lascar/60 text-xs">{sectionIcon(section.title)}</span>
            <h2 className="font-display text-xs uppercase tracking-[0.2em] text-or-lascar">
              {section.title}
            </h2>
          </div>
          {section.body ? (
            <MarkdownBody text={section.body} />
          ) : (
            <p className="text-xs text-blanc-linen/25 italic">Aucune donnée disponible.</p>
          )}
        </div>
      ))}
    </div>
  )
}
