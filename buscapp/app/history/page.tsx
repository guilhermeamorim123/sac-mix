'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { HistoryCard } from '@/components/HistoryCard'
import { getHistory } from '@/lib/storage'
import type { ProductAnalysis } from '@/lib/types'

export default function HistoryPage() {
  const [history, setHistory] = useState<ProductAnalysis[]>([])

  useEffect(() => {
    setHistory(getHistory())
  }, [])

  return (
    <main className="min-h-screen p-5 pb-10">
      <div className="flex items-center justify-between pt-2 mb-6">
        <h1 className="text-primary font-bold text-xl tracking-widest">BUSCAPP</h1>
        <Link href="/" className="text-text-secondary text-sm active:opacity-70">📷 Analisar</Link>
      </div>

      <h2 className="text-text-primary font-semibold text-lg mb-4">Histórico</h2>

      {history.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-text-secondary text-center">Nenhuma análise ainda.</p>
          <Link href="/" className="bg-primary text-black font-bold py-3 px-8 rounded-xl">
            Fazer primeira análise
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((analysis) => (
            <HistoryCard key={analysis.id} analysis={analysis} />
          ))}
        </div>
      )}
    </main>
  )
}
