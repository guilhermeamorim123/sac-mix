'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { VerdictBadge } from '@/components/VerdictBadge'
import { ReportCard } from '@/components/ReportCard'
import { getVehicleAnalysis } from '@/lib/storage'
import type { VehicleAnalysis } from '@/lib/types'

function AutoReportContent() {
  const router = useRouter()
  const params = useSearchParams()
  const [report, setReport] = useState<VehicleAnalysis | null>(null)

  useEffect(() => {
    const id = params.get('id')
    if (id) {
      const saved = getVehicleAnalysis(id)
      if (saved) { setReport(saved); return }
    }
    const raw = sessionStorage.getItem('buscapp_auto_report')
    if (raw) {
      try { setReport(JSON.parse(raw)) } catch { router.push('/auto') }
    } else {
      router.push('/auto')
    }
  }, [router, params])

  if (!report) return null

  const fmt = (n: number) => n.toLocaleString('pt-BR')
  const vsFIPE = report.market.vsFIPE

  return (
    <main className="min-h-screen p-5 pb-10 space-y-5">
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-primary font-bold text-xl tracking-widest">BUSCAPP</h1>
      </div>

      {/* Vehicle ID */}
      <div className="bg-surface border border-border rounded-xl p-4">
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">
          {report.vehicle.category} · {report.vehicle.year}
        </p>
        <p className="text-text-primary font-bold text-lg leading-tight">
          {report.vehicle.brand} {report.vehicle.model}
        </p>
        <p className="text-text-secondary text-sm">{report.vehicle.version}</p>
        {report.plate && (
          <span className="inline-block mt-2 bg-surface border border-primary text-primary text-xs font-bold tracking-widest px-2 py-0.5 rounded">
            {report.plate}
          </span>
        )}
      </div>

      {/* Prices */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">💰 Preços</p>
        <div className="grid grid-cols-2 gap-2">
          <ReportCard label="Tabela FIPE" value={`R$ ${fmt(report.prices.fipe)}`} />
          <ReportCard label="Média Mercado" value={`R$ ${fmt(report.prices.marketAvg)}`} />
          <ReportCard label="Mín." value={`R$ ${fmt(report.prices.marketMin)}`} />
          <ReportCard label="Máx." value={`R$ ${fmt(report.prices.marketMax)}`} />
        </div>
        {vsFIPE !== 0 && (
          <p className="text-text-secondary text-xs mt-2">
            Mercado está{' '}
            <span className={vsFIPE > 0 ? 'text-primary' : 'text-danger'}>
              {vsFIPE > 0 ? '+' : ''}{vsFIPE.toFixed(1)}%
            </span>{' '}
            em relação à FIPE
          </p>
        )}
      </section>

      {/* Specs */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">⚙️ Especificações Técnicas</p>
        <div className="grid grid-cols-2 gap-2">
          <ReportCard label="Potência" value={`${report.specs.horsepower} CV`} valueClassName="text-primary" />
          <ReportCard label="Torque" value={report.specs.torque} />
          <ReportCard label="Motor" value={report.specs.engine} />
          <ReportCard label="Câmbio" value={report.specs.transmission} />
          <ReportCard label="Consumo (cidade)" value={`${report.specs.fuelCity} km/l`} />
          <ReportCard label="Consumo (estrada)" value={`${report.specs.fuelHighway} km/l`} />
        </div>
      </section>

      {/* Listings */}
      {report.market.listings.length > 0 && (
        <section>
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">
            📋 Anúncios Webmotors
            {report.market.listingsCount > 0 && (
              <span className="ml-1 normal-case">({report.market.listingsCount} encontrados)</span>
            )}
          </p>
          <div className="space-y-2">
            {report.market.listings.map((listing, i) => (
              <div key={i} className="bg-surface border border-border rounded-xl p-3">
                <p className="text-text-primary text-sm font-medium">{listing.title}</p>
                <p className="text-text-secondary text-xs mt-0.5">{listing.km} · {listing.city}</p>
                <p className="text-primary text-sm font-bold mt-1">R$ {fmt(listing.price)}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Verdict */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🏆 Veredito</p>
        <VerdictBadge rating={report.verdict.rating} />
        <p className="text-text-secondary text-sm mt-2 text-center">{report.verdict.justification}</p>
      </section>

      <button
        onClick={() => router.push('/auto')}
        className="w-full bg-primary text-black font-bold py-4 rounded-xl text-base active:opacity-80"
      >
        🚗 Nova Análise
      </button>
    </main>
  )
}

export default function AutoReportPage() {
  return (
    <Suspense fallback={null}>
      <AutoReportContent />
    </Suspense>
  )
}
