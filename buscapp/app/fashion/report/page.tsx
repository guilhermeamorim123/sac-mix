'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AuthenticityBar } from '@/components/AuthenticityBar'
import { getFashionAnalysis } from '@/lib/storage'
import type { FashionAnalysis, AuthenticityVerdict, SignalStatus } from '@/lib/types'

const SIGNAL_ICON: Record<SignalStatus, string> = {
  ok: '✅',
  warning: '⚠️',
  fail: '❌',
}

const VERDICT_STYLES: Record<AuthenticityVerdict, { bg: string; text: string }> = {
  ORIGINAL: { bg: 'bg-success',  text: 'text-black' },
  SUSPEITO: { bg: 'bg-warning',  text: 'text-black' },
  'RÉPLICA':  { bg: 'bg-danger',   text: 'text-white' },
}

function FashionReportContent() {
  const router = useRouter()
  const params = useSearchParams()
  const [report, setReport] = useState<FashionAnalysis | null>(null)

  useEffect(() => {
    const id = params.get('id')
    if (id) {
      const saved = getFashionAnalysis(id)
      if (saved) { setReport(saved); return }
    }
    const raw = sessionStorage.getItem('buscapp_fashion_report')
    if (raw) {
      try { setReport(JSON.parse(raw)) } catch { router.push('/fashion') }
    } else {
      router.push('/fashion')
    }
  }, [router, params])

  if (!report) return null

  const { bg, text } = VERDICT_STYLES[report.authenticity.verdict]

  return (
    <main className="min-h-screen p-5 pb-10 space-y-5">
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-primary font-bold text-xl tracking-widest">BUSCAPP</h1>
      </div>

      {/* Item ID */}
      <div className="bg-surface border border-border rounded-xl p-4">
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">
          {report.item.category} · {report.item.itemType}
        </p>
        <p className="text-text-primary font-bold text-lg leading-tight">
          {report.item.brand} {report.item.model}
        </p>
        <p className="text-text-secondary text-sm">{report.item.colorway} · {report.item.year}</p>
      </div>

      {/* Authenticity Score */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🔍 Autenticidade</p>
        <AuthenticityBar score={report.authenticity.score} verdict={report.authenticity.verdict} />
      </section>

      {/* Signals */}
      {report.authenticity.signals.length > 0 && (
        <section>
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">Sinais Observados</p>
          <div className="bg-surface border border-border rounded-xl divide-y divide-border">
            {report.authenticity.signals.map((signal, i) => (
              <div key={i} className="flex items-start gap-3 p-3">
                <span className="text-base flex-shrink-0 mt-0.5">{SIGNAL_ICON[signal.status]}</span>
                <p className="text-text-primary text-sm">{signal.detail}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Market Prices */}
      {report.prices.platforms.length > 0 && (
        <section>
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">💰 Preço de Mercado</p>
          <div className="space-y-2">
            {report.prices.platforms.map((p, i) => (
              <div key={i} className="flex justify-between items-center bg-surface border border-border rounded-xl px-4 py-3">
                <p className="text-text-secondary text-sm">{p.name}</p>
                <p className="text-primary font-bold text-sm">{p.price}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Verdict */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🏆 Veredito</p>
        <div className={`${bg} ${text} w-full py-4 rounded-xl text-center font-bold text-lg uppercase tracking-widest`}>
          {report.authenticity.verdict}
        </div>
      </section>

      <button
        onClick={() => router.push('/fashion')}
        className="w-full bg-primary text-black font-bold py-4 rounded-xl text-base active:opacity-80"
      >
        👗 Nova Análise
      </button>
    </main>
  )
}

export default function FashionReportPage() {
  return (
    <Suspense fallback={null}>
      <FashionReportContent />
    </Suspense>
  )
}
