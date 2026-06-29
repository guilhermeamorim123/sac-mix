'use client'
import { useRef } from 'react'

interface CameraButtonProps {
  onCapture: (base64: string) => void
  captureMode?: boolean  // default: true — uses device camera. false = gallery/file picker
}

export function CameraButton({ onCapture, captureMode = true }: CameraButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    const img = new Image()
    const objectUrl = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      const MAX = 1200
      let { width, height } = img
      if (width > MAX || height > MAX) {
        if (width > height) { height = Math.round((height * MAX) / width); width = MAX }
        else { width = Math.round((width * MAX) / height); height = MAX }
      }
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d')!.drawImage(img, 0, 0, width, height)
      const base64 = canvas.toDataURL('image/jpeg', 0.8)
      onCapture(base64)
    }
    img.src = objectUrl
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        {...(captureMode ? { capture: 'environment' as const } : {})}
        className="hidden"
        onChange={handleFile}
      />
      <button
        onClick={() => inputRef.current?.click()}
        className="w-24 h-24 rounded-full bg-primary flex items-center justify-center animate-pulse shadow-[0_0_30px_rgba(34,197,94,0.4)] active:scale-95 transition-transform"
        aria-label="Fotografar produto"
      >
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
      </button>
    </>
  )
}
