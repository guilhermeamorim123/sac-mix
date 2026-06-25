interface ReportCardProps {
  label: string
  value: string | number
  icon?: string
  valueClassName?: string
}

export function ReportCard({ label, value, icon, valueClassName = '' }: ReportCardProps) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
      {icon && <span className="text-2xl">{icon}</span>}
      <div className="flex-1 min-w-0">
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-0.5">{label}</p>
        <p className={`text-text-primary font-semibold truncate ${valueClassName}`}>{value}</p>
      </div>
    </div>
  )
}
