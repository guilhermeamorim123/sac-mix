import type { VerdictRating } from '@/lib/types'

const config: Record<VerdictRating, { bg: string; text: string; emoji: string }> = {
  'VALE INVESTIR': { bg: 'bg-success', text: 'text-black', emoji: '🟢' },
  'ATENÇÃO':       { bg: 'bg-warning', text: 'text-black', emoji: '🟡' },
  'NÃO VALE':      { bg: 'bg-danger',  text: 'text-white', emoji: '🔴' },
}

interface VerdictBadgeProps {
  rating: VerdictRating
  mini?: boolean
}

export function VerdictBadge({ rating, mini = false }: VerdictBadgeProps) {
  const { bg, text, emoji } = config[rating]

  if (mini) {
    return (
      <span className={`${bg} ${text} text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wide`}>
        {emoji} {rating}
      </span>
    )
  }

  return (
    <div className={`${bg} ${text} w-full py-4 rounded-xl text-center font-bold text-lg uppercase tracking-widest`}>
      {emoji} {rating}
    </div>
  )
}
