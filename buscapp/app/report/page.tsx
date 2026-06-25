'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { VerdictBadge } from '@/components/VerdictBadge'
import { ReportCard } from '@/components/ReportCard'
import { getAnalysis } from '@/lib/storage'
import type { ProductAnalysis } from '@/lib/types'

function ReportContent() {
  const router = useRouter()
  const params = useSearchParams()
  const [report, setReport] = useState<ProductAnalysis | null>(null)

  useEffect(() => {
    const id = params.get('id')

    if (id) {
      const saved = getAnalysis(id)
      if (saved) { setReport(saved); return }
    }

    const raw = sessionStorage.getItem('buscapp_report')
    if (raw) {
      try { setReport(JSON.parse(raw)) } catch { router.push('/') }
    } else {
      router.push('/')
    }
  }, [router, params])

  if (!report) return null

  const priceRange = `R$ ${report.prices.min.toLocaleString('pt-BR')} — R$ ${report.prices.max.toLocaleString('pt-BR')}`
  const avgPrice = `R$ ${report.prices.avg.toLocaleString('pt-BR')}`
  const profit = `R$ ${report.investment.profitPerUnit.toLocaleString('pt-BR')} / unidade`
  const margin = `${report.investment.marginPercent}%`

  return (
    <main className="min-h-screen p-5 pb-10 space-y-5">
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-primary font-bold text-xl tracking-widest">BUSCAPP</h1>
        <Link href="/history" className="text-text-secondary text-sm active:opacity-70">🕐</Link>
      </div>

      <div className="bg-surface border border-border rounded-xl p-4">
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">{report.product.category}</p>
        <p className="text-text-primary font-bold text-lg leading-tight">{report.product.name}</p>
        <p className="text-text-secondary text-sm">{report.product.brand} · {report.product.model}</p>
      </div>

      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">💰 Preços no Mercado</p>
        <div className="grid grid-cols-2 gap-2">
          <ReportCard label="Preço Médio" value={avgPrice} />
          <ReportCard label="Faixa de Preço" value={priceRange} />
        </div>
        <p className="text-text-secondary text-xs mt-2">Vendendo em: {report.prices.platforms.join(', ')}</p>
      </section>

      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">📊 Análise de Mercado</p>
        <div className="grid grid-cols-3 gap-2">
          <ReportCard label="Volume" value={report.market.salesVolume} />
          <ReportCard label="Concorrência" value={report.market.competition} />
          <ReportCard label="Tendência" value={report.market.trend} />
        </div>
        <div className="bg-surface border border-border rounded-xl p-4 mt-2">
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">⭐ Avaliações</p>
          <p className="text-text-primary text-sm">{report.market.reviewSummary}</p>
        </div>
      </section>

      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">💡 Análise de Investimento</p>
        <div className="grid grid-cols-2 gap-2">
          <ReportCard label="Lucro Estimado" value={profit} valueClassName="text-primary" />
          <ReportCard label="Margem" value={margin} valueClassName="text-primary" />
          <ReportCard label="Preço Sugerido" value={`R$ ${report.investment.suggestedPrice.toLocaleString('pt-BR')}`} />
          <ReportCard label="Risco" value={report.investment.riskLevel} />
        </div>
      </section>

      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🏆 Veredito</p>
        <VerdictBadge rating={report.verdict.rating} />
        <p className="text-text-secondary text-sm mt-2 text-center">{report.verdict.justification}</p>
      </section>

      {report.similarProducts.length > 0 && (
        <section>
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🔍 Produtos Similares</p>
          <div className="space-y-2">
            {report.similarProducts.map((p, i) => (
              <div key={i} className="bg-surface border border-border rounded-xl p-3">
                <p className="text-text-primary text-sm font-medium">{p.name}</p>
                <p className="text-text-secondary text-xs mt-0.5">{p.note}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <button
        onClick={() => router.push('/')}
        className="w-full bg-primary text-black font-bold py-4 rounded-xl text-base active:opacity-80"
      >
        📷 Nova Análise
      </button>
    </main>
  )
}

export default function ReportPage() {
  return (
    <Suspense fallback={null}>
      <ReportContent />
    </Suspense>
  )
}
