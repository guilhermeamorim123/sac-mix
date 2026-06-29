'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProgressBar } from '@/components/ProgressBar'
import { saveVehicleAnalysis } from '@/lib/storage'

const MESSAGES = [
  'Identificando o veículo...',
  'Consultando Tabela FIPE...',
  'Buscando anúncios no Webmotors...',
  'Verificando especificações técnicas...',
  'Calculando análise de mercado...',
  'Montando relatório...',
]

export default function AutoAnalyzingPage() {
  const router = useRouter()
  const [msgIndex, setMsgIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const interval = setInterval(() => setMsgIndex(i => (i + 1) % MESSAGES.length), 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const imageBase64 = sessionStorage.getItem('buscapp_auto_image')
    const plate = sessionStorage.getItem('buscapp_auto_plate') ?? ''
    if (!imageBase64) { router.push('/auto'); return }

    fetch('/api/auto/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageBase64, plate }),
    })
      .then(async res => {
        if (!res.ok) { const b = await res.json(); throw new Error(b.error || 'Erro na análise') }
        return res.json()
      })
      .then(analysis => {
        saveVehicleAnalysis(analysis)
        sessionStorage.setItem('buscapp_auto_report', JSON.stringify(analysis))
        sessionStorage.removeItem('buscapp_auto_image')
        sessionStorage.removeItem('buscapp_auto_plate')
        router.push('/auto/report')
      })
      .catch((err: Error) => setError(err.message))
  }, [router])

  if (error) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen p-6 gap-6">
        <p className="text-danger text-center">{error}</p>
        <button
          onClick={() => router.push('/auto')}
          className="bg-primary text-black font-bold py-3 px-8 rounded-xl"
        >
          Tentar novamente
        </button>
      </main>
    )
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-6 gap-8">
      <h1 className="text-primary font-bold text-2xl tracking-widest">BUSCAPP</h1>
      <div className="w-full max-w-sm space-y-4">
        <ProgressBar />
        <p className="text-text-secondary text-center text-sm transition-all duration-500">
          {MESSAGES[msgIndex]}
        </p>
      </div>
    </main>
  )
}
