# BUSCAPP Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Upload, Auto (veículos), and Fashion (autenticidade premium) tabs to BUSCAPP via a shared bottom tab bar.

**Architecture:** Shared types/storage/TabBar foundation first, then three independent feature tracks (Upload reuses existing API, Auto and Fashion each get new Claude functions + Tavily functions + API route + pages). Each feature track can be tested end-to-end before starting the next.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS (custom tokens in `tailwind.config.ts`), Anthropic SDK (claude-sonnet-4-6), Tavily API, Jest + node environment for API tests.

---

## File Map

**New files (13):**
- `components/TabBar.tsx`
- `components/AuthenticityBar.tsx`
- `app/upload/page.tsx`
- `app/auto/page.tsx`
- `app/auto/analyzing/page.tsx`
- `app/auto/report/page.tsx`
- `app/fashion/page.tsx`
- `app/fashion/analyzing/page.tsx`
- `app/fashion/report/page.tsx`
- `app/api/auto/analyze/route.ts`
- `app/api/fashion/analyze/route.ts`
- `__tests__/api/auto-analyze.test.ts`
- `__tests__/api/fashion-analyze.test.ts`

**Modified files (6):**
- `lib/types.ts` — add VehicleAnalysis, FashionAnalysis and their sub-types
- `lib/storage.ts` — add vehicle and fashion history functions
- `lib/claude.ts` — add identifyVehicle, synthesizeAutoReport, identifyFashionItem, synthesizeFashionPrices
- `lib/tavily.ts` — add searchVehicle, searchFashionItem
- `components/CameraButton.tsx` — add optional `captureMode` prop
- `app/page.tsx` — add TabBar, adjust padding

**Extended test files (4):**
- `__tests__/lib/storage.test.ts` — add vehicle/fashion tests
- `__tests__/lib/claude.test.ts` — add vehicle/fashion function tests
- `__tests__/lib/tavily.test.ts` — add vehicle/fashion search tests

---

## Task 1: Extend Types

**Files:**
- Modify: `lib/types.ts`

- [ ] **Step 1: Add vehicle and fashion types to `lib/types.ts`**

Append after the last existing export:

```typescript
// ── Vehicle (Auto tab) ────────────────────────────────────────────────

export interface VehicleInfo {
  brand: string
  model: string
  year: string
  version: string
  category: string
}

export interface VehicleSpecs {
  horsepower: number
  torque: string
  engine: string
  transmission: string
  fuelCity: number
  fuelHighway: number
}

export interface VehiclePrices {
  fipe: number
  marketAvg: number
  marketMin: number
  marketMax: number
}

export interface VehicleListing {
  title: string
  price: number
  km: string
  city: string
}

export interface VehicleMarket {
  listings: VehicleListing[]
  listingsCount: number
  liquidity: 'Alta' | 'Média' | 'Baixa'
  vsFIPE: number
}

export interface VehicleAnalysis {
  id: string
  createdAt: string
  plate?: string
  vehicle: VehicleInfo
  prices: VehiclePrices
  specs: VehicleSpecs
  market: VehicleMarket
  verdict: Verdict
}

// ── Fashion (Moda tab) ────────────────────────────────────────────────

export type AuthenticityVerdict = 'ORIGINAL' | 'SUSPEITO' | 'RÉPLICA'
export type SignalStatus = 'ok' | 'warning' | 'fail'

export interface AuthenticitySignal {
  status: SignalStatus
  detail: string
}

export interface FashionItem {
  brand: string
  model: string
  colorway: string
  year: string
  category: string
  itemType: string
}

export interface FashionAuthenticity {
  score: number
  verdict: AuthenticityVerdict
  signals: AuthenticitySignal[]
}

export interface FashionPlatformPrice {
  name: string
  price: string
  currency: 'BRL' | 'USD'
}

export interface FashionPrices {
  platforms: FashionPlatformPrice[]
}

export interface FashionAnalysis {
  id: string
  createdAt: string
  item: FashionItem
  authenticity: FashionAuthenticity
  prices: FashionPrices
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd buscapp && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add buscapp/lib/types.ts
git commit -m "feat(buscapp): add VehicleAnalysis and FashionAnalysis types"
```

---

## Task 2: Extend Storage

**Files:**
- Modify: `lib/storage.ts`
- Modify: `__tests__/lib/storage.test.ts`

- [ ] **Step 1: Write failing tests — append to `__tests__/lib/storage.test.ts`**

```typescript
import {
  saveVehicleAnalysis, getVehicleHistory, getVehicleAnalysis,
  saveFashionAnalysis, getFashionHistory, getFashionAnalysis,
} from '@/lib/storage'
import type { VehicleAnalysis, FashionAnalysis } from '@/lib/types'

const mockVehicle: VehicleAnalysis = {
  id: 'auto-1',
  createdAt: '2026-06-29T10:00:00Z',
  plate: 'ABC-1D23',
  vehicle: { brand: 'Toyota', model: 'Corolla', year: '2022', version: 'XEi', category: 'Sedan' },
  prices: { fipe: 112000, marketAvg: 118000, marketMin: 108000, marketMax: 128000 },
  specs: { horsepower: 177, torque: '20,4 kgfm', engine: '2.0 Flex', transmission: 'CVT', fuelCity: 10.8, fuelHighway: 13.1 },
  market: { listings: [], listingsCount: 342, liquidity: 'Alta', vsFIPE: 5.4 },
  verdict: { rating: 'VALE INVESTIR', justification: 'Alta liquidez' },
}

const mockFashion: FashionAnalysis = {
  id: 'fashion-1',
  createdAt: '2026-06-29T10:00:00Z',
  item: { brand: 'Nike', model: 'Air Jordan 1', colorway: 'Chicago', year: '2019', category: 'Calçado', itemType: 'Tênis' },
  authenticity: { score: 82, verdict: 'ORIGINAL', signals: [{ status: 'ok', detail: 'Costura uniforme' }] },
  prices: { platforms: [{ name: 'Nike.com.br', price: 'R$ 1.299', currency: 'BRL' }] },
}

describe('vehicle storage', () => {
  beforeEach(() => { localStorage.clear() })

  it('saveVehicleAnalysis persiste no localStorage', () => {
    saveVehicleAnalysis(mockVehicle)
    const raw = localStorage.getItem('buscapp_auto_history')
    expect(JSON.parse(raw!)[0].id).toBe('auto-1')
  })

  it('getVehicleHistory retorna lista salva', () => {
    saveVehicleAnalysis(mockVehicle)
    expect(getVehicleHistory()).toHaveLength(1)
    expect(getVehicleHistory()[0].vehicle.brand).toBe('Toyota')
  })

  it('getVehicleAnalysis encontra por id', () => {
    saveVehicleAnalysis(mockVehicle)
    expect(getVehicleAnalysis('auto-1')?.plate).toBe('ABC-1D23')
  })

  it('getVehicleAnalysis retorna null se não existe', () => {
    expect(getVehicleAnalysis('nao-existe')).toBeNull()
  })

  it('getVehicleHistory retorna [] quando vazio', () => {
    expect(getVehicleHistory()).toEqual([])
  })
})

describe('fashion storage', () => {
  beforeEach(() => { localStorage.clear() })

  it('saveFashionAnalysis persiste no localStorage', () => {
    saveFashionAnalysis(mockFashion)
    const raw = localStorage.getItem('buscapp_fashion_history')
    expect(JSON.parse(raw!)[0].id).toBe('fashion-1')
  })

  it('getFashionHistory retorna lista salva', () => {
    saveFashionAnalysis(mockFashion)
    expect(getFashionHistory()).toHaveLength(1)
    expect(getFashionHistory()[0].item.brand).toBe('Nike')
  })

  it('getFashionAnalysis encontra por id', () => {
    saveFashionAnalysis(mockFashion)
    expect(getFashionAnalysis('fashion-1')?.authenticity.verdict).toBe('ORIGINAL')
  })

  it('getFashionAnalysis retorna null se não existe', () => {
    expect(getFashionAnalysis('nao-existe')).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd buscapp && npx jest __tests__/lib/storage.test.ts
```

Expected: FAIL — `saveVehicleAnalysis is not a function` (or similar).

- [ ] **Step 3: Implement — append to `lib/storage.ts`**

```typescript
import type { VehicleAnalysis, FashionAnalysis } from './types'

const AUTO_KEY = 'buscapp_auto_history'
const FASHION_KEY = 'buscapp_fashion_history'

export function saveVehicleAnalysis(analysis: VehicleAnalysis): void {
  const history = getVehicleHistory()
  history.unshift(analysis)
  localStorage.setItem(AUTO_KEY, JSON.stringify(history.slice(0, 50)))
}

export function getVehicleHistory(): VehicleAnalysis[] {
  if (typeof window === 'undefined') return []
  const raw = localStorage.getItem(AUTO_KEY)
  if (!raw) return []
  try { return JSON.parse(raw) as VehicleAnalysis[] } catch { return [] }
}

export function getVehicleAnalysis(id: string): VehicleAnalysis | null {
  return getVehicleHistory().find(a => a.id === id) ?? null
}

export function saveFashionAnalysis(analysis: FashionAnalysis): void {
  const history = getFashionHistory()
  history.unshift(analysis)
  localStorage.setItem(FASHION_KEY, JSON.stringify(history.slice(0, 50)))
}

export function getFashionHistory(): FashionAnalysis[] {
  if (typeof window === 'undefined') return []
  const raw = localStorage.getItem(FASHION_KEY)
  if (!raw) return []
  try { return JSON.parse(raw) as FashionAnalysis[] } catch { return [] }
}

export function getFashionAnalysis(id: string): FashionAnalysis | null {
  return getFashionHistory().find(a => a.id === id) ?? null
}
```

Note: the existing `import type { ProductAnalysis } from './types'` at the top of `lib/storage.ts` should stay. Add the new import separately or merge into the existing import line.

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd buscapp && npx jest __tests__/lib/storage.test.ts
```

Expected: all tests PASS (existing + new).

- [ ] **Step 5: Commit**

```bash
git add buscapp/lib/storage.ts buscapp/__tests__/lib/storage.test.ts
git commit -m "feat(buscapp): add vehicle and fashion storage functions"
```

---

## Task 3: CameraButton — Gallery Mode

**Files:**
- Modify: `components/CameraButton.tsx`

- [ ] **Step 1: Add optional `captureMode` prop**

Replace the `CameraButtonProps` interface and the `<input>` element:

```typescript
interface CameraButtonProps {
  onCapture: (base64: string) => void
  captureMode?: boolean  // default: true — uses device camera. false = gallery/file picker
}

export function CameraButton({ onCapture, captureMode = true }: CameraButtonProps) {
```

In the JSX, change the `<input>` from:

```typescript
<input
  ref={inputRef}
  type="file"
  accept="image/*"
  capture="environment"
  className="hidden"
  onChange={handleFile}
/>
```

to:

```typescript
<input
  ref={inputRef}
  type="file"
  accept="image/*"
  {...(captureMode ? { capture: 'environment' as const } : {})}
  className="hidden"
  onChange={handleFile}
/>
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd buscapp && npx jest
```

Expected: all existing tests PASS (the prop is optional with a default, no breaking change).

- [ ] **Step 3: Commit**

```bash
git add buscapp/components/CameraButton.tsx
git commit -m "feat(buscapp): add captureMode prop to CameraButton for gallery support"
```

---

## Task 4: TabBar Component

**Files:**
- Create: `components/TabBar.tsx`

- [ ] **Step 1: Create `components/TabBar.tsx`**

```typescript
'use client'
import Link from 'next/link'

export type ActiveTab = 'camera' | 'upload' | 'auto' | 'fashion'

const TABS: { id: ActiveTab; icon: string; label: string; href: string }[] = [
  { id: 'camera',  icon: '📷', label: 'Câmera', href: '/' },
  { id: 'upload',  icon: '🖼️', label: 'Upload',  href: '/upload' },
  { id: 'auto',    icon: '🚗', label: 'Auto',    href: '/auto' },
  { id: 'fashion', icon: '👗', label: 'Moda',    href: '/fashion' },
]

interface TabBarProps {
  active: ActiveTab
}

export function TabBar({ active }: TabBarProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-background border-t border-border flex h-16 z-50">
      {TABS.map(tab => (
        <Link
          key={tab.id}
          href={tab.href}
          className={`flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors active:opacity-70 ${
            active === tab.id ? 'text-primary' : 'text-text-secondary'
          }`}
        >
          <span className="text-xl leading-none">{tab.icon}</span>
          <span className={`text-[10px] ${active === tab.id ? 'font-semibold' : ''}`}>
            {tab.label}
          </span>
        </Link>
      ))}
    </nav>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd buscapp && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add buscapp/components/TabBar.tsx
git commit -m "feat(buscapp): add TabBar component with 4 tabs"
```

---

## Task 5: Upload Page

**Files:**
- Create: `app/upload/page.tsx`

- [ ] **Step 1: Create `app/upload/page.tsx`**

```typescript
'use client'
import { useRouter } from 'next/navigation'
import { CameraButton } from '@/components/CameraButton'
import { TabBar } from '@/components/TabBar'

export default function UploadPage() {
  const router = useRouter()

  function handleCapture(base64: string) {
    sessionStorage.setItem('buscapp_image', base64)
    router.push('/analyzing')
  }

  return (
    <main className="flex flex-col items-center justify-between min-h-screen p-6 pb-24">
      <div className="w-full flex justify-between items-center pt-4">
        <h1 className="text-primary font-bold text-2xl tracking-widest">BUSCAPP</h1>
      </div>

      <div className="flex flex-col items-center gap-6">
        <div className="text-center">
          <p className="text-text-secondary text-sm">Selecione uma imagem ou print</p>
          <p className="text-text-secondary text-xs mt-1">e receba análise de mercado em segundos</p>
        </div>
        <CameraButton onCapture={handleCapture} captureMode={false} />
        <p className="text-text-secondary text-xs">Toque para selecionar</p>
      </div>

      <p className="text-border text-xs">BUSCAPP • Análise de Mercado com IA</p>
      <TabBar active="upload" />
    </main>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add buscapp/app/upload/page.tsx
git commit -m "feat(buscapp): add Upload tab — gallery image analysis"
```

---

## Task 6: Update Existing Home and Report Pages

**Files:**
- Modify: `app/page.tsx`
- Modify: `app/report/page.tsx`

- [ ] **Step 1: Update `app/page.tsx`**

Add `TabBar` import and replace existing content:

```typescript
'use client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { CameraButton } from '@/components/CameraButton'
import { TabBar } from '@/components/TabBar'

export default function HomePage() {
  const router = useRouter()

  function handleCapture(base64: string) {
    sessionStorage.setItem('buscapp_image', base64)
    router.push('/analyzing')
  }

  return (
    <main className="flex flex-col items-center justify-between min-h-screen p-6 pb-24">
      <div className="w-full flex justify-between items-center pt-4">
        <h1 className="text-primary font-bold text-2xl tracking-widest">BUSCAPP</h1>
        <Link href="/history" className="text-text-secondary text-sm active:opacity-70">🕐</Link>
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
      <TabBar active="camera" />
    </main>
  )
}
```

- [ ] **Step 2: Update `app/report/page.tsx`**

Add `TabBar` import at the top of the file alongside existing imports:

```typescript
import { TabBar } from '@/components/TabBar'
```

In `ReportContent`, change the `<main>` opening tag to include bottom padding and add `<TabBar>` before the closing `</main>`:

```typescript
// Change:
<main className="min-h-screen p-5 pb-10 space-y-5">
// To:
<main className="min-h-screen p-5 pb-28 space-y-5">
```

Add just before `</main>`:

```typescript
      <TabBar active="camera" />
```

- [ ] **Step 3: Start dev server and verify home + camera + report flow still works**

```bash
cd buscapp && npm run dev
```

Open http://localhost:3000. Verify:
- Tab bar appears at bottom on home page with Camera tab highlighted
- Tap Upload tab → goes to `/upload` with gallery picker
- History icon (🕐) still visible in header on home

- [ ] **Step 4: Commit**

```bash
git add buscapp/app/page.tsx buscapp/app/report/page.tsx
git commit -m "feat(buscapp): add TabBar to home and report pages"
```

---

## Task 7: Auto — Claude Functions

**Files:**
- Modify: `lib/claude.ts`
- Modify: `__tests__/lib/claude.test.ts`

- [ ] **Step 1: Write failing tests — append to `__tests__/lib/claude.test.ts`**

```typescript
import { identifyVehicle, synthesizeAutoReport, identifyFashionItem, synthesizeFashionPrices } from '@/lib/claude'

describe('identifyVehicle', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('retorna dados do veículo a partir de imagem', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        brand: 'Toyota', model: 'Corolla', year: '2022',
        version: 'XEi 2.0', category: 'Sedan',
      })}],
    })

    const result = await identifyVehicle('fake-base64')

    expect(result.brand).toBe('Toyota')
    expect(result.model).toBe('Corolla')
    expect(result.year).toBe('2022')
  })

  it('inclui a placa no prompt quando fornecida', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        brand: 'Honda', model: 'Civic', year: '2021', version: 'EXL', category: 'Sedan',
      })}],
    })

    await identifyVehicle('fake-base64', 'XYZ-9876')

    const callArgs = mockCreate.mock.calls[0][0]
    const textContent = callArgs.messages[0].content.find((c: { type: string }) => c.type === 'text')
    expect(textContent.text).toContain('XYZ-9876')
  })
})

describe('synthesizeAutoReport', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('retorna relatório estruturado de veículo', async () => {
    const mockAutoReport = {
      prices: { fipe: 112000, marketAvg: 118000, marketMin: 108000, marketMax: 128000 },
      specs: { horsepower: 177, torque: '20,4 kgfm', engine: '2.0 Flex', transmission: 'CVT', fuelCity: 10.8, fuelHighway: 13.1 },
      market: { listings: [], listingsCount: 342, liquidity: 'Alta', vsFIPE: 5.4 },
      verdict: { rating: 'VALE INVESTIR', justification: 'Alta liquidez' },
    }

    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify(mockAutoReport) }],
    })

    const vehicle = { brand: 'Toyota', model: 'Corolla', year: '2022', version: 'XEi', category: 'Sedan' }
    const result = await synthesizeAutoReport(vehicle, ['resultado 1'])

    expect(result.specs.horsepower).toBe(177)
    expect(result.prices.fipe).toBe(112000)
    expect(result.verdict.rating).toBe('VALE INVESTIR')
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd buscapp && npx jest __tests__/lib/claude.test.ts
```

Expected: FAIL — `identifyVehicle is not a function`.

- [ ] **Step 3: Implement — append to `lib/claude.ts`**

First add the missing type imports at the top of the file. Find the existing import line:

```typescript
import type { ProductInfo, PriceInfo, MarketInfo, InvestmentInfo, Verdict, SimilarProduct } from './types'
```

Replace with:

```typescript
import type {
  ProductInfo, PriceInfo, MarketInfo, InvestmentInfo, Verdict, SimilarProduct,
  VehicleInfo, VehicleSpecs, VehiclePrices, VehicleMarket,
  FashionItem, FashionAuthenticity, FashionPrices, AuthenticityVerdict,
} from './types'
```

Then append to the end of `lib/claude.ts`:

```typescript
export async function identifyVehicle(imageBase64: string, plate?: string): Promise<VehicleInfo> {
  const plateHint = plate ? `\nA placa do veículo é: ${plate}` : ''
  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 300,
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 },
        },
        {
          type: 'text',
          text: `Identifique o veículo nesta imagem.${plateHint}\nResponda APENAS com JSON válido neste formato exato, sem markdown:\n{"brand":"marca","model":"modelo","year":"ano","version":"versão/acabamento","category":"categoria (ex: Sedan, SUV, Hatchback, Picape, Moto)"}`,
        },
      ],
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : ''
  return JSON.parse(extractJson(text)) as VehicleInfo
}

export async function synthesizeAutoReport(
  vehicle: VehicleInfo,
  searchResults: string[]
): Promise<{ prices: VehiclePrices; specs: VehicleSpecs; market: VehicleMarket; verdict: Verdict }> {
  const resultsText = searchResults.join('\n\n---\n\n')

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2000,
    messages: [{
      role: 'user',
      content: `Você é um especialista em avaliação de veículos para revendedores brasileiros.

Veículo: ${vehicle.brand} ${vehicle.model} ${vehicle.year} ${vehicle.version}

Resultados de busca:
${resultsText}

Gere um relatório em JSON válido (sem markdown):

{
  "prices": {
    "fipe": <número em reais>,
    "marketAvg": <número em reais>,
    "marketMin": <número em reais>,
    "marketMax": <número em reais>
  },
  "specs": {
    "horsepower": <número em CV>,
    "torque": "<string, ex: 20,4 kgfm>",
    "engine": "<string, ex: 2.0 Flex>",
    "transmission": "<CVT | Automático | Manual>",
    "fuelCity": <número km/l>,
    "fuelHighway": <número km/l>
  },
  "market": {
    "listings": [{"title":"<anúncio>","price":<número>,"km":"<string>","city":"<cidade, UF>"}],
    "listingsCount": <número total>,
    "liquidity": "Alta" | "Média" | "Baixa",
    "vsFIPE": <diferença % entre marketAvg e fipe, pode ser negativo>
  },
  "verdict": {
    "rating": "VALE INVESTIR" | "ATENÇÃO" | "NÃO VALE",
    "justification": "<1-2 frases>"
  }
}

Máximo 5 itens em listings. Use 0 para campos numéricos sem dados. Sempre retorne JSON válido.`,
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return JSON.parse(extractJson(text))
}
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd buscapp && npx jest __tests__/lib/claude.test.ts
```

Expected: all tests PASS (existing + new vehicle tests). Fashion tests not yet added — only vehicle tests added in this task.

- [ ] **Step 5: Commit**

```bash
git add buscapp/lib/claude.ts buscapp/__tests__/lib/claude.test.ts
git commit -m "feat(buscapp): add identifyVehicle and synthesizeAutoReport to claude lib"
```

---

## Task 8: Auto — Tavily Functions

**Files:**
- Modify: `lib/tavily.ts`
- Modify: `__tests__/lib/tavily.test.ts`

- [ ] **Step 1: Write failing tests — append to `__tests__/lib/tavily.test.ts`**

```typescript
import { searchVehicle } from '@/lib/tavily'

describe('searchVehicle', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.TAVILY_API_KEY = 'test-key'
  })

  it('executa 5 buscas em paralelo para veículo', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((_url: string, opts: RequestInit) => {
      const body = JSON.parse(opts.body as string)
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          results: [{ content: `resultado: ${body.query}`, url: 'http://example.com', title: 'Título' }],
        }),
      })
    })

    const results = await searchVehicle('Toyota Corolla 2022 XEi')

    expect(global.fetch).toHaveBeenCalledTimes(5)
    expect(results).toHaveLength(5)
  })

  it('lança erro se TAVILY_API_KEY não estiver definida', async () => {
    delete process.env.TAVILY_API_KEY
    await expect(searchVehicle('Toyota Corolla')).rejects.toThrow('TAVILY_API_KEY')
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd buscapp && npx jest __tests__/lib/tavily.test.ts
```

Expected: FAIL — `searchVehicle is not a function`.

- [ ] **Step 3: Implement — append to `lib/tavily.ts`**

```typescript
export async function searchVehicle(vehicleQuery: string): Promise<string[]> {
  const apiKey = process.env.TAVILY_API_KEY
  if (!apiKey) throw new Error('TAVILY_API_KEY não configurada')

  const queries = [
    `${vehicleQuery} tabela FIPE valor 2025`,
    `${vehicleQuery} Webmotors comprar preço anúncios`,
    `${vehicleQuery} especificações cavalos torque motor câmbio`,
    `${vehicleQuery} consumo combustível km litro`,
    `${vehicleQuery} anúncios venda km rodados`,
  ]

  return Promise.all(queries.map(q => tavilySearch(q, apiKey)))
}
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd buscapp && npx jest __tests__/lib/tavily.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add buscapp/lib/tavily.ts buscapp/__tests__/lib/tavily.test.ts
git commit -m "feat(buscapp): add searchVehicle to tavily lib"
```

---

## Task 9: Auto — API Route

**Files:**
- Create: `app/api/auto/analyze/route.ts`
- Create: `__tests__/api/auto-analyze.test.ts`

- [ ] **Step 1: Write failing test — create `__tests__/api/auto-analyze.test.ts`**

```typescript
/**
 * @jest-environment node
 */
import { POST } from '@/app/api/auto/analyze/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/claude', () => ({
  identifyVehicle: jest.fn().mockResolvedValue({
    brand: 'Toyota', model: 'Corolla', year: '2022', version: 'XEi', category: 'Sedan',
  }),
  synthesizeAutoReport: jest.fn().mockResolvedValue({
    prices: { fipe: 112000, marketAvg: 118000, marketMin: 108000, marketMax: 128000 },
    specs: { horsepower: 177, torque: '20,4 kgfm', engine: '2.0 Flex', transmission: 'CVT', fuelCity: 10.8, fuelHighway: 13.1 },
    market: { listings: [], listingsCount: 342, liquidity: 'Alta', vsFIPE: 5.4 },
    verdict: { rating: 'VALE INVESTIR', justification: 'Alta liquidez' },
  }),
}))

jest.mock('@/lib/tavily', () => ({
  searchVehicle: jest.fn().mockResolvedValue(['resultado 1', 'resultado 2']),
}))

describe('POST /api/auto/analyze', () => {
  it('retorna VehicleAnalysis completo dado imageBase64', async () => {
    const req = new NextRequest('http://localhost/api/auto/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64', plate: 'ABC-1D23' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.vehicle.brand).toBe('Toyota')
    expect(body.specs.horsepower).toBe(177)
    expect(body.plate).toBe('ABC-1D23')
    expect(body.id).toBeDefined()
  })

  it('funciona sem placa (plate opcional)', async () => {
    const req = new NextRequest('http://localhost/api/auto/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.plate).toBeUndefined()
  })

  it('retorna 400 se imageBase64 não for enviado', async () => {
    const req = new NextRequest('http://localhost/api/auto/analyze', {
      method: 'POST',
      body: JSON.stringify({ plate: 'ABC-1D23' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
cd buscapp && npx jest __tests__/api/auto-analyze.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `app/api/auto/analyze/route.ts`**

The route does NOT call `saveVehicleAnalysis` — saving happens on the client (in `/auto/analyzing`) after it receives the response, matching the same pattern as `/api/analyze`.

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { identifyVehicle, synthesizeAutoReport } from '@/lib/claude'
import { searchVehicle } from '@/lib/tavily'
import type { VehicleAnalysis } from '@/lib/types'

export const maxDuration = 60

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { imageBase64, plate } = body

    if (!imageBase64 || typeof imageBase64 !== 'string') {
      return NextResponse.json({ error: 'imageBase64 obrigatório' }, { status: 400 })
    }

    const base64Data = imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64

    const vehicle = await identifyVehicle(base64Data, plate || undefined)
    const vehicleQuery = `${vehicle.brand} ${vehicle.model} ${vehicle.year} ${vehicle.version}`
    const searchResults = await searchVehicle(vehicleQuery)
    const report = await synthesizeAutoReport(vehicle, searchResults)

    const analysis: VehicleAnalysis = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      ...(plate ? { plate } : {}),
      vehicle,
      ...report,
    }

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('[/api/auto/analyze]', error)
    return NextResponse.json({ error: 'Erro ao analisar veículo. Tente novamente.' }, { status: 500 })
  }
}
```

- [ ] **Step 4: Run test — confirm it passes**

```bash
cd buscapp && npx jest __tests__/api/auto-analyze.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add buscapp/app/api/auto/analyze/route.ts buscapp/__tests__/api/auto-analyze.test.ts
git commit -m "feat(buscapp): add /api/auto/analyze route"
```

---

## Task 10: Auto — Pages

**Files:**
- Create: `app/auto/page.tsx`
- Create: `app/auto/analyzing/page.tsx`
- Create: `app/auto/report/page.tsx`

- [ ] **Step 1: Create `app/auto/page.tsx`**

```typescript
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
```

- [ ] **Step 2: Create `app/auto/analyzing/page.tsx`**

```typescript
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
```

- [ ] **Step 3: Create `app/auto/report/page.tsx`**

```typescript
'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { VerdictBadge } from '@/components/VerdictBadge'
import { ReportCard } from '@/components/ReportCard'
import { TabBar } from '@/components/TabBar'
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
    <main className="min-h-screen p-5 pb-28 space-y-5">
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

      <TabBar active="auto" />
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
```

- [ ] **Step 4: Test the Auto flow end-to-end**

```bash
cd buscapp && npm run dev
```

With a valid `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` in `.env.local`:
1. Open http://localhost:3000/auto
2. Tab bar shows with Auto highlighted
3. Camera button opens camera; plate field is always visible below
4. After capturing, navigates to `/auto/analyzing` with vehicle-specific messages
5. After analysis, navigates to `/auto/report` with prices → specs → listings → verdict

- [ ] **Step 5: Commit**

```bash
git add buscapp/app/auto/
git commit -m "feat(buscapp): add Auto tab — vehicle analysis with FIPE, specs, and Webmotors listings"
```

---

## Task 11: Fashion — Claude Functions

**Files:**
- Modify: `lib/claude.ts`
- Modify: `__tests__/lib/claude.test.ts`

- [ ] **Step 1: Write failing tests — append to `__tests__/lib/claude.test.ts`**

```typescript
describe('identifyFashionItem', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('retorna item identificado com score e sinais', async () => {
    const mockResponse = {
      brand: 'Nike', model: 'Air Jordan 1', colorway: 'Chicago',
      year: '2019', category: 'Calçado', itemType: 'Tênis',
      authenticityScore: 82,
      signals: [
        { status: 'ok', detail: 'Costura uniforme' },
        { status: 'warning', detail: 'Etiqueta não visível' },
      ],
    }

    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify(mockResponse) }],
    })

    const result = await identifyFashionItem('fake-base64')

    expect(result.item.brand).toBe('Nike')
    expect(result.authenticity.score).toBe(82)
    expect(result.authenticity.verdict).toBe('ORIGINAL')
    expect(result.authenticity.signals).toHaveLength(2)
  })

  it('mapeia score < 40 para RÉPLICA', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        brand: 'Louis Vuitton', model: 'Neverfull', colorway: 'Monogram',
        year: '2023', category: 'Bolsa', itemType: 'Tote',
        authenticityScore: 25, signals: [],
      })}],
    })

    const result = await identifyFashionItem('fake-base64')

    expect(result.authenticity.verdict).toBe('RÉPLICA')
  })

  it('mapeia score 40-69 para SUSPEITO', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        brand: 'Gucci', model: 'Marmont', colorway: 'Black',
        year: '2022', category: 'Bolsa', itemType: 'Shoulder Bag',
        authenticityScore: 55, signals: [],
      })}],
    })

    const result = await identifyFashionItem('fake-base64')

    expect(result.authenticity.verdict).toBe('SUSPEITO')
  })
})

describe('synthesizeFashionPrices', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('retorna preços por plataforma', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        platforms: [
          { name: 'Nike.com.br', price: 'R$ 1.299', currency: 'BRL' },
          { name: 'StockX', price: 'US$ 180', currency: 'USD' },
        ],
      })}],
    })

    const item = { brand: 'Nike', model: 'Air Jordan 1', colorway: 'Chicago', year: '2019', category: 'Calçado', itemType: 'Tênis' }
    const result = await synthesizeFashionPrices(item, ['resultado 1'])

    expect(result.platforms).toHaveLength(2)
    expect(result.platforms[0].name).toBe('Nike.com.br')
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd buscapp && npx jest __tests__/lib/claude.test.ts
```

Expected: FAIL — `identifyFashionItem is not a function`.

- [ ] **Step 3: Implement — append to `lib/claude.ts`**

```typescript
export async function identifyFashionItem(imageBase64: string): Promise<{
  item: FashionItem
  authenticity: { score: number; verdict: AuthenticityVerdict; signals: import('./types').AuthenticitySignal[] }
}> {
  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 800,
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 },
        },
        {
          type: 'text',
          text: `Analise esta peça de roupa ou acessório. Identifique o item E avalie sinais de autenticidade.
Responda APENAS com JSON válido neste formato, sem markdown:
{
  "brand": "marca",
  "model": "modelo específico",
  "colorway": "nome do colorway ou cor",
  "year": "ano de lançamento estimado",
  "category": "Calçado | Bolsa | Roupa | Acessório | Relógio | Joia",
  "itemType": "tipo específico (ex: Tênis, Jaqueta, Carteira)",
  "authenticityScore": <número 0-100>,
  "signals": [{"status": "ok" | "warning" | "fail", "detail": "descrição do sinal"}]
}
Para authenticityScore: avalie costura, logotipo, proporções, acabamento visível.
Para signals: liste 3-6 sinais específicos.
Se não identificar a marca, use "Marca não identificada".`,
        },
      ],
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : ''
  const parsed = JSON.parse(extractJson(text))

  const score: number = parsed.authenticityScore ?? 0
  const verdict: AuthenticityVerdict = score >= 70 ? 'ORIGINAL' : score >= 40 ? 'SUSPEITO' : 'RÉPLICA'

  return {
    item: {
      brand: parsed.brand,
      model: parsed.model,
      colorway: parsed.colorway,
      year: parsed.year,
      category: parsed.category,
      itemType: parsed.itemType,
    },
    authenticity: { score, verdict, signals: parsed.signals ?? [] },
  }
}

export async function synthesizeFashionPrices(
  item: FashionItem,
  searchResults: string[]
): Promise<FashionPrices> {
  const resultsText = searchResults.join('\n\n---\n\n')

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 600,
    messages: [{
      role: 'user',
      content: `Extraia preços de mercado para este item a partir dos resultados de busca.

Item: ${item.brand} ${item.model} ${item.colorway}

Resultados:
${resultsText}

Responda APENAS com JSON válido (sem markdown):
{"platforms":[{"name":"nome da plataforma","price":"valor formatado (ex: R$ 1.299 ou US$ 180)","currency":"BRL" | "USD"}]}

Máximo 4 plataformas. Se não houver dados, retorne {"platforms":[]}.`,
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return JSON.parse(extractJson(text))
}
```

Fix the import — replace the inline `import('./types').AuthenticitySignal[]` with the type from the top-level import. Update the import line added in Task 7 to also include `AuthenticitySignal`:

```typescript
import type {
  ProductInfo, PriceInfo, MarketInfo, InvestmentInfo, Verdict, SimilarProduct,
  VehicleInfo, VehicleSpecs, VehiclePrices, VehicleMarket,
  FashionItem, FashionAuthenticity, FashionPrices, AuthenticityVerdict, AuthenticitySignal,
} from './types'
```

Then update `identifyFashionItem` return signature:

```typescript
export async function identifyFashionItem(imageBase64: string): Promise<{
  item: FashionItem
  authenticity: { score: number; verdict: AuthenticityVerdict; signals: AuthenticitySignal[] }
}>
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd buscapp && npx jest __tests__/lib/claude.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add buscapp/lib/claude.ts buscapp/__tests__/lib/claude.test.ts
git commit -m "feat(buscapp): add identifyFashionItem and synthesizeFashionPrices to claude lib"
```

---

## Task 12: Fashion — Tavily Functions

**Files:**
- Modify: `lib/tavily.ts`
- Modify: `__tests__/lib/tavily.test.ts`

- [ ] **Step 1: Write failing tests — append to `__tests__/lib/tavily.test.ts`**

```typescript
import { searchFashionItem } from '@/lib/tavily'

describe('searchFashionItem', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.TAVILY_API_KEY = 'test-key'
  })

  it('executa 3 buscas em paralelo para item de moda', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((_url: string, opts: RequestInit) => {
      const body = JSON.parse(opts.body as string)
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          results: [{ content: `resultado: ${body.query}`, url: 'http://example.com', title: 'Título' }],
        }),
      })
    })

    const results = await searchFashionItem('Nike Air Jordan 1 Chicago')

    expect(global.fetch).toHaveBeenCalledTimes(3)
    expect(results).toHaveLength(3)
  })

  it('lança erro se TAVILY_API_KEY não estiver definida', async () => {
    delete process.env.TAVILY_API_KEY
    await expect(searchFashionItem('Nike Air Jordan 1')).rejects.toThrow('TAVILY_API_KEY')
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd buscapp && npx jest __tests__/lib/tavily.test.ts
```

Expected: FAIL — `searchFashionItem is not a function`.

- [ ] **Step 3: Implement — append to `lib/tavily.ts`**

```typescript
export async function searchFashionItem(itemQuery: string): Promise<string[]> {
  const apiKey = process.env.TAVILY_API_KEY
  if (!apiKey) throw new Error('TAVILY_API_KEY não configurada')

  const queries = [
    `${itemQuery} preço oficial brasil site comprar`,
    `${itemQuery} farfetch stockx preço dolar real`,
    `${itemQuery} original vs fake como identificar autenticidade`,
  ]

  return Promise.all(queries.map(q => tavilySearch(q, apiKey)))
}
```

- [ ] **Step 4: Run all tests**

```bash
cd buscapp && npx jest __tests__/lib/tavily.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add buscapp/lib/tavily.ts buscapp/__tests__/lib/tavily.test.ts
git commit -m "feat(buscapp): add searchFashionItem to tavily lib"
```

---

## Task 13: Fashion — API Route

**Files:**
- Create: `app/api/fashion/analyze/route.ts`
- Create: `__tests__/api/fashion-analyze.test.ts`

- [ ] **Step 1: Write failing test — create `__tests__/api/fashion-analyze.test.ts`**

```typescript
/**
 * @jest-environment node
 */
import { POST } from '@/app/api/fashion/analyze/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/claude', () => ({
  identifyFashionItem: jest.fn().mockResolvedValue({
    item: { brand: 'Nike', model: 'Air Jordan 1', colorway: 'Chicago', year: '2019', category: 'Calçado', itemType: 'Tênis' },
    authenticity: { score: 82, verdict: 'ORIGINAL', signals: [{ status: 'ok', detail: 'Costura uniforme' }] },
  }),
  synthesizeFashionPrices: jest.fn().mockResolvedValue({
    platforms: [{ name: 'Nike.com.br', price: 'R$ 1.299', currency: 'BRL' }],
  }),
}))

jest.mock('@/lib/tavily', () => ({
  searchFashionItem: jest.fn().mockResolvedValue(['resultado 1', 'resultado 2']),
}))

describe('POST /api/fashion/analyze', () => {
  it('retorna FashionAnalysis completo dado imageBase64', async () => {
    const req = new NextRequest('http://localhost/api/fashion/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.item.brand).toBe('Nike')
    expect(body.authenticity.score).toBe(82)
    expect(body.authenticity.verdict).toBe('ORIGINAL')
    expect(body.prices.platforms).toHaveLength(1)
    expect(body.id).toBeDefined()
  })

  it('retorna 400 se imageBase64 não for enviado', async () => {
    const req = new NextRequest('http://localhost/api/fashion/analyze', {
      method: 'POST',
      body: JSON.stringify({}),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
cd buscapp && npx jest __tests__/api/fashion-analyze.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `app/api/fashion/analyze/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { identifyFashionItem, synthesizeFashionPrices } from '@/lib/claude'
import { searchFashionItem } from '@/lib/tavily'
import type { FashionAnalysis } from '@/lib/types'

export const maxDuration = 60

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { imageBase64 } = body

    if (!imageBase64 || typeof imageBase64 !== 'string') {
      return NextResponse.json({ error: 'imageBase64 obrigatório' }, { status: 400 })
    }

    const base64Data = imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64

    const { item, authenticity } = await identifyFashionItem(base64Data)
    const itemQuery = `${item.brand} ${item.model} ${item.colorway}`
    const searchResults = await searchFashionItem(itemQuery)
    const prices = await synthesizeFashionPrices(item, searchResults)

    const analysis: FashionAnalysis = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      item,
      authenticity,
      prices,
    }

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('[/api/fashion/analyze]', error)
    return NextResponse.json({ error: 'Erro ao analisar peça. Tente novamente.' }, { status: 500 })
  }
}
```

- [ ] **Step 4: Run test — confirm it passes**

```bash
cd buscapp && npx jest __tests__/api/fashion-analyze.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Run all tests**

```bash
cd buscapp && npx jest
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add buscapp/app/api/fashion/analyze/route.ts buscapp/__tests__/api/fashion-analyze.test.ts
git commit -m "feat(buscapp): add /api/fashion/analyze route"
```

---

## Task 14: AuthenticityBar Component

**Files:**
- Create: `components/AuthenticityBar.tsx`

- [ ] **Step 1: Create `components/AuthenticityBar.tsx`**

```typescript
import type { AuthenticityVerdict } from '@/lib/types'

interface AuthenticityBarProps {
  score: number
  verdict: AuthenticityVerdict
}

const COLORS: Record<AuthenticityVerdict, string> = {
  ORIGINAL: '#22C55E',
  SUSPEITO: '#F59E0B',
  RÉPLICA:  '#EF4444',
}

const LABELS: Record<AuthenticityVerdict, string> = {
  ORIGINAL: 'Provavelmente Original',
  SUSPEITO: 'Suspeito',
  RÉPLICA:  'Provável Réplica',
}

export function AuthenticityBar({ score, verdict }: AuthenticityBarProps) {
  const color = COLORS[verdict]
  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <div className="flex justify-between items-center mb-2">
        <p className="text-text-secondary text-xs uppercase tracking-wide">Score de Autenticidade</p>
        <p className="text-sm font-bold" style={{ color }}>
          {score}%
        </p>
      </div>
      <div className="h-2 bg-border rounded-full overflow-hidden mb-2">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <p className="text-xs font-semibold" style={{ color }}>{LABELS[verdict]}</p>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd buscapp && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add buscapp/components/AuthenticityBar.tsx
git commit -m "feat(buscapp): add AuthenticityBar component"
```

---

## Task 15: Fashion — Pages

**Files:**
- Create: `app/fashion/page.tsx`
- Create: `app/fashion/analyzing/page.tsx`
- Create: `app/fashion/report/page.tsx`

- [ ] **Step 1: Create `app/fashion/page.tsx`**

```typescript
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
```

- [ ] **Step 2: Create `app/fashion/analyzing/page.tsx`**

```typescript
'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProgressBar } from '@/components/ProgressBar'
import { saveFashionAnalysis } from '@/lib/storage'

const MESSAGES = [
  'Identificando a peça...',
  'Analisando marca e modelo...',
  'Verificando sinais de autenticidade...',
  'Buscando preços oficiais...',
  'Consultando mercado premium...',
  'Montando relatório...',
]

export default function FashionAnalyzingPage() {
  const router = useRouter()
  const [msgIndex, setMsgIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const interval = setInterval(() => setMsgIndex(i => (i + 1) % MESSAGES.length), 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const imageBase64 = sessionStorage.getItem('buscapp_fashion_image')
    if (!imageBase64) { router.push('/fashion'); return }

    fetch('/api/fashion/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageBase64 }),
    })
      .then(async res => {
        if (!res.ok) { const b = await res.json(); throw new Error(b.error || 'Erro na análise') }
        return res.json()
      })
      .then(analysis => {
        saveFashionAnalysis(analysis)
        sessionStorage.setItem('buscapp_fashion_report', JSON.stringify(analysis))
        sessionStorage.removeItem('buscapp_fashion_image')
        router.push('/fashion/report')
      })
      .catch((err: Error) => setError(err.message))
  }, [router])

  if (error) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen p-6 gap-6">
        <p className="text-danger text-center">{error}</p>
        <button
          onClick={() => router.push('/fashion')}
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
```

- [ ] **Step 3: Create `app/fashion/report/page.tsx`**

```typescript
'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AuthenticityBar } from '@/components/AuthenticityBar'
import { TabBar } from '@/components/TabBar'
import { getFashionAnalysis } from '@/lib/storage'
import type { FashionAnalysis, AuthenticityVerdict, SignalStatus } from '@/lib/types'

const SIGNAL_ICON: Record<SignalStatus, string> = {
  ok: '✅',
  warning: '⚠️',
  fail: '❌',
}

const VERDICT_STYLES: Record<AuthenticityVerdict, { bg: string; text: string }> = {
  ORIGINAL: { bg: 'bg-success',  text: 'text-black' },
  SUSPEITO: { bg: 'bg-warning',  text: 'text-black' },
  RÉPLICA:  { bg: 'bg-danger',   text: 'text-white' },
}

function FashionReportContent() {
  const router = useRouter()
  const params = useSearchParams()
  const [report, setReport] = useState<FashionAnalysis | null>(null)

  useEffect(() => {
    const id = params.get('id')
    if (id) {
      const saved = getFashionAnalysis(id)
      if (saved) { setReport(saved); return }
    }
    const raw = sessionStorage.getItem('buscapp_fashion_report')
    if (raw) {
      try { setReport(JSON.parse(raw)) } catch { router.push('/fashion') }
    } else {
      router.push('/fashion')
    }
  }, [router, params])

  if (!report) return null

  const { bg, text } = VERDICT_STYLES[report.authenticity.verdict]

  return (
    <main className="min-h-screen p-5 pb-28 space-y-5">
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-primary font-bold text-xl tracking-widest">BUSCAPP</h1>
      </div>

      {/* Item ID */}
      <div className="bg-surface border border-border rounded-xl p-4">
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">
          {report.item.category} · {report.item.itemType}
        </p>
        <p className="text-text-primary font-bold text-lg leading-tight">
          {report.item.brand} {report.item.model}
        </p>
        <p className="text-text-secondary text-sm">{report.item.colorway} · {report.item.year}</p>
      </div>

      {/* Authenticity Score */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🔍 Autenticidade</p>
        <AuthenticityBar score={report.authenticity.score} verdict={report.authenticity.verdict} />
      </section>

      {/* Signals */}
      {report.authenticity.signals.length > 0 && (
        <section>
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">Sinais Observados</p>
          <div className="bg-surface border border-border rounded-xl divide-y divide-border">
            {report.authenticity.signals.map((signal, i) => (
              <div key={i} className="flex items-start gap-3 p-3">
                <span className="text-base flex-shrink-0 mt-0.5">{SIGNAL_ICON[signal.status]}</span>
                <p className="text-text-primary text-sm">{signal.detail}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Market Prices */}
      {report.prices.platforms.length > 0 && (
        <section>
          <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">💰 Preço de Mercado</p>
          <div className="space-y-2">
            {report.prices.platforms.map((p, i) => (
              <div key={i} className="flex justify-between items-center bg-surface border border-border rounded-xl px-4 py-3">
                <p className="text-text-secondary text-sm">{p.name}</p>
                <p className="text-primary font-bold text-sm">{p.price}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Verdict */}
      <section>
        <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">🏆 Veredito</p>
        <div className={`${bg} ${text} w-full py-4 rounded-xl text-center font-bold text-lg uppercase tracking-widest`}>
          {report.authenticity.verdict}
        </div>
      </section>

      <button
        onClick={() => router.push('/fashion')}
        className="w-full bg-primary text-black font-bold py-4 rounded-xl text-base active:opacity-80"
      >
        👗 Nova Análise
      </button>

      <TabBar active="fashion" />
    </main>
  )
}

export default function FashionReportPage() {
  return (
    <Suspense fallback={null}>
      <FashionReportContent />
    </Suspense>
  )
}
```

- [ ] **Step 4: Run all tests**

```bash
cd buscapp && npx jest
```

Expected: all tests PASS.

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd buscapp && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Test Fashion flow end-to-end**

```bash
cd buscapp && npm run dev
```

1. Open http://localhost:3000/fashion
2. Tab bar shows with Moda highlighted
3. Camera captures image → `/fashion/analyzing` with fashion-specific messages
4. Report shows: item ID → score bar → signals → prices → verdict badge (colored by result)

- [ ] **Step 7: Final commit**

```bash
git add buscapp/app/fashion/ buscapp/components/AuthenticityBar.tsx
git commit -m "feat(buscapp): add Fashion tab — brand identification and authenticity scoring"
```

---

## Final Verification

- [ ] **Run all tests one last time**

```bash
cd buscapp && npx jest
```

Expected: all tests PASS.

- [ ] **TypeScript check**

```bash
cd buscapp && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Manual smoke test — all 4 tabs**

```bash
cd buscapp && npm run dev
```

Verify:
- `/` — Câmera tab highlighted, camera opens on button tap
- `/upload` — Upload tab highlighted, gallery opens on button tap, same report as camera
- `/auto` — Auto tab highlighted, camera + plate field both visible
- `/fashion` — Moda tab highlighted, camera opens
- Tab bar always visible on capture pages, hidden on analyzing pages
- History (🕐) accessible from home header
