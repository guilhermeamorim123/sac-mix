export function ProgressBar() {
  return (
    <div className="w-full h-1 bg-surface-elevated rounded-full overflow-hidden">
      <div
        className="h-full bg-primary rounded-full"
        style={{
          width: '40%',
          animation: 'progressSlide 1.5s ease-in-out infinite',
        }}
      />
      <style>{`
        @keyframes progressSlide {
          0% { transform: translateX(-250%); width: 40%; }
          50% { width: 60%; }
          100% { transform: translateX(350%); width: 40%; }
        }
      `}</style>
    </div>
  )
}
