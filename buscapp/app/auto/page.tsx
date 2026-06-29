'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { CameraButton } from '@/components/CameraButton'
import { TabBar } from '@/components/TabBar'

export default function AutoPage() {
  const router = useRouter()
  const [plate, setPlate] = useState('')

  function handleCapture(base64: string) {
    sessionStorage.setItem('buscapp_auto_image', base64)
    sessionStorage.setItem('buscapp_auto_plate', plate.trim())
    router.push('/auto/analyzing')
  }

  return (
    <main className="flex flex-col items-center justify-between min-h-screen p-6 pb-24">
      <div className="w-full flex justify-between items-center pt-4">
        <h1 className="text-primary font-bold text-2xl tracking-widest">BUSCAPP</h1>
      </div>

      <div className="flex flex-col items-center gap-6 w-full max-w-sm">
        <div className="text-center">
          <p className="text-text-secondary text-sm">Fotografe o veículo</p>
          <p className="text-text-secondary text-xs mt-1">specs técnicos, FIPE e anúncios Webmotors</p>
        </div>
        <CameraButton onCapture={handleCapture} />
        <div className="w-full">
          <label className="block text-text-secondary text-xs uppercase tracking-wide mb-1">
            Placa (opcional)
          </label>
          <input
            type="text"
            value={plate}
            onChange={e => setPlate(e.target.value.toUpperCase())}
            placeholder="ABC-1D23"
            maxLength={8}
            className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-text-primary text-sm tracking-widest placeholder:text-text-secondary focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      <p className="text-border text-xs">BUSCAPP • Análise de Veículos com IA</p>
      <TabBar active="auto" />
    </main>
  )
}
