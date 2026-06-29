import type { AuthenticityVerdict } from '@/lib/types'

interface AuthenticityBarProps {
  score: number
  verdict: AuthenticityVerdict
}

const COLORS: Record<AuthenticityVerdict, string> = {
  ORIGINAL: '#22C55E',
  SUSPEITO: '#F59E0B',
  'RÉPLICA':  '#EF4444',
}

const LABELS: Record<AuthenticityVerdict, string> = {
  ORIGINAL: 'Provavelmente Original',
  SUSPEITO: 'Suspeito',
  'RÉPLICA':  'Provável Réplica',
}

export function AuthenticityBar({ score, verdict }: AuthenticityBarProps) {
  const color = COLORS[verdict]
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <div className="flex justify-between items-center mb-2">
        <p className="text-text-secondary text-xs uppercase tracking-wide">Score de Autenticidade</p>
        <p className="text-sm font-bold" style={{ color }}>
          {score}%
        </p>
      </div>
      <div className="h-2 bg-border rounded-full overflow-hidden mb-2">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <p className="text-xs font-semibold" style={{ color }}>{LABELS[verdict]}</p>
    </div>
  )
}
