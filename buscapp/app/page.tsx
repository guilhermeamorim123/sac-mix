'use client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { CameraButton } from '@/components/CameraButton'

export default function HomePage() {
  const router = useRouter()

  function handleCapture(base64: string) {
    sessionStorage.setItem('buscapp_image', base64)
    router.push('/analyzing')
  }

  return (
    <main className="flex flex-col items-center justify-between min-h-screen p-6 pb-10">
      <div className="w-full flex justify-between items-center pt-4">
        <h1 className="text-primary font-bold text-2xl tracking-widest">BUSCAPP</h1>
        <Link href="/history" className="text-text-secondary text-sm flex items-center gap-1 active:opacity-70">
          🕐 Histórico
        </Link>
      </div>

      <div className="flex flex-col items-center gap-6">
        <div className="text-center">
          <p className="text-text-secondary text-sm">Aponte para qualquer produto</p>
          <p className="text-text-secondary text-xs mt-1">e receba análise de mercado em segundos</p>
        </div>
        <CameraButton onCapture={handleCapture} />
        <p className="text-text-secondary text-xs">Toque para fotografar</p>
      </div>

      <p className="text-border text-xs">BUSCAPP • Análise de Mercado com IA</p>
    </main>
  )
}
