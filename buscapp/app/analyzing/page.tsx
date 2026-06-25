'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProgressBar } from '@/components/ProgressBar'
import { saveAnalysis } from '@/lib/storage'

const MESSAGES = [
  'Identificando produto...',
  'Buscando preços no mercado...',
  'Analisando concorrência...',
  'Verificando tendências...',
  'Calculando margem de lucro...',
  'Montando relatório...',
]

export default function AnalyzingPage() {
  const router = useRouter()
  const [msgIndex, setMsgIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIndex((i) => (i + 1) % MESSAGES.length)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const imageBase64 = sessionStorage.getItem('buscapp_image')
    if (!imageBase64) {
      router.push('/')
      return
    }

    fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageBase64 }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json()
          throw new Error(body.error || 'Erro na análise')
        }
        return res.json()
      })
      .then((analysis) => {
        saveAnalysis(analysis)
        sessionStorage.setItem('buscapp_report', JSON.stringify(analysis))
        sessionStorage.removeItem('buscapp_image')
        router.push('/report')
      })
      .catch((err: Error) => {
        setError(err.message)
      })
  }, [router])

  if (error) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen p-6 gap-6">
        <p className="text-danger text-center">{error}</p>
        <button
          onClick={() => router.push('/')}
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
