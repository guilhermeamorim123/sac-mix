import Link from 'next/link'
import { VerdictBadge } from './VerdictBadge'
import type { ProductAnalysis } from '@/lib/types'

interface HistoryCardProps {
  analysis: ProductAnalysis
}

export function HistoryCard({ analysis }: HistoryCardProps) {
  const date = new Date(analysis.createdAt).toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  })

  return (
    <Link href={`/report?id=${analysis.id}`}>
      <div className="bg-surface border border-border rounded-xl p-4 flex items-center justify-between gap-3 active:opacity-70">
        <div className="flex-1 min-w-0">
          <p className="text-text-primary font-medium truncate">{analysis.product.name}</p>
          <p className="text-text-secondary text-xs mt-0.5">{date}</p>
        </div>
        <VerdictBadge rating={analysis.verdict.rating} mini />
      </div>
    </Link>
  )
}
