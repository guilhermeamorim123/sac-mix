'use client'
import { useRouter } from 'next/navigation'
import { CameraButton } from '@/components/CameraButton'
import { TabBar } from '@/components/TabBar'

export default function FashionPage() {
  const router = useRouter()

  function handleCapture(base64: string) {
    sessionStorage.setItem('buscapp_fashion_image', base64)
    router.push('/fashion/analyzing')
  }

  return (
    <main className="flex flex-col items-center justify-between min-h-screen p-6 pb-24">
      <div className="w-full flex justify-between items-center pt-4">
        <h1 className="text-primary font-bold text-2xl tracking-widest">BUSCAPP</h1>
      </div>

      <div className="flex flex-col items-center gap-6">
        <div className="text-center">
          <p className="text-text-secondary text-sm">Fotografe a peça ou acessório</p>
          <p className="text-text-secondary text-xs mt-1">identificação de marca e análise de autenticidade</p>
        </div>
        <CameraButton onCapture={handleCapture} />
        <p className="text-text-secondary text-xs">Toque para fotografar</p>
      </div>

      <p className="text-border text-xs">BUSCAPP • Autenticidade com IA</p>
      <TabBar active="fashion" />
    </main>
  )
}
