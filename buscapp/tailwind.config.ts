import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0A0A0A',
        surface: '#141414',
        'surface-elevated': '#1E1E1E',
        primary: '#22C55E',
        'primary-dark': '#16A34A',
        'text-primary': '#FFFFFF',
        'text-secondary': '#9CA3AF',
        border: '#2A2A2A',
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.05)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        pulse: 'pulse 2s ease-in-out infinite',
        shimmer: 'shimmer 1.5s linear infinite',
      },
    },
  },
  plugins: [],
}

export default config
