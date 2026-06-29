# BUSCAPP Expansion — Design Spec
**Date:** 2026-06-29  
**Status:** Approved

## Overview

Add 3 new tabs to BUSCAPP, turning a single-mode product scanner into a 4-mode analysis platform. All modes share the same dark theme, tab bar navigation, and history storage.

---

## Navigation

Replace the current top-right link to Histórico with a **bottom tab bar** fixed to the viewport. Four tabs:

| Tab | Icon | Route |
|-----|------|-------|
| Câmera | 📷 | `/` (existing home) |
| Upload | 🖼️ | `/upload` |
| Auto | 🚗 | `/auto` |
| Moda | 👗 | `/fashion` |

The tab bar renders on every page except `/analyzing`, `/auto/analyzing`, `/fashion/analyzing`, `/report`, `/auto/report`, `/fashion/report`, and `/history`. Active tab is highlighted in `#22c55e`.

The existing top-right "🕐 Histórico" link is removed from all pages — history is accessed via a dedicated route linked from the tab bar or a header icon.

---

## Tab 1 — Upload (🖼️)

**Purpose:** Same market analysis as the Câmera tab but the image comes from the device gallery instead of the live camera.

**Capture screen (`/upload`):**  
Identical to the current home (`/`) but the `CameraButton` renders without `capture="environment"`, opening the file picker / gallery. Label changes to "Selecione uma imagem ou print".

**Analysis flow:** Reuses `/api/analyze` unchanged. After capture, stores base64 in `sessionStorage` under `buscapp_image` and navigates to `/analyzing` — same page already in production.

**Report:** Reuses `/report` unchanged.

**What changes:** Only the capture screen. Zero new API routes or report components.

---

## Tab 2 — Auto (🚗)

### Capture Screen (`/auto`)

Layout has two stacked sections:
1. `CameraButton` (with `capture="environment"`) — labeled "Fotografe o veículo"
2. A text input field always visible below: **"Placa (opcional)"** — accepts Brazilian plate format (ABC-1D23 / ABC1D23). Always rendered, never conditional.

On capture: saves base64 + plate string to `sessionStorage` (`buscapp_auto_image`, `buscapp_auto_plate`), navigates to `/auto/analyzing`.

### Analyzing Screen (`/auto/analyzing`)

Same cycling messages pattern, adapted:
- "Identificando o veículo..."
- "Consultando Tabela FIPE..."
- "Buscando anúncios no Webmotors..."
- "Verificando especificações técnicas..."
- "Calculando análise de mercado..."
- "Montando relatório..."

Calls `POST /api/auto/analyze` with `{ imageBase64, plate }`.

### API Route — `/api/auto/analyze`

**Step 1 — Identify vehicle (Claude Vision):**  
Send image to `claude-sonnet-4-6`. Extract: `{ brand, model, year, version, category }`. If plate is provided, include it in the prompt as additional context.

**Step 2 — Web search (Tavily):**  
Run 5 parallel queries:
- `"[brand] [model] [year] tabela FIPE valor"`
- `"[brand] [model] [year] Webmotors comprar preço"`
- `"[brand] [model] [year] especificações cavalos torque motor"`
- `"[brand] [model] [year] consumo combustível km/l"`
- `"[brand] [model] [year] anúncios venda km"`

**Step 3 — Synthesize (Claude):**  
Produce JSON:
```ts
{
  vehicle: { brand, model, year, version, category },
  prices: { fipe: number, marketAvg: number, marketMin: number, marketMax: number },
  specs: {
    horsepower: number,       // CV
    torque: string,           // "20,4 kgfm"
    engine: string,           // "2.0 Flex"
    transmission: string,     // "CVT" | "Automático" | "Manual"
    fuelCity: number,         // km/l
    fuelHighway: number       // km/l
  },
  market: {
    listings: Array<{ title: string, price: number, km: string, city: string }>,  // max 5
    listingsCount: number,
    liquidity: "Alta" | "Média" | "Baixa",
    vsFIPE: number            // % difference market avg vs FIPE
  },
  verdict: { rating: "VALE INVESTIR" | "ATENÇÃO" | "NÃO VALE", justification: string }
}
```

### Report Screen (`/auto/report`)

Sections in order:
1. **Vehicle ID card** — brand, model, year, version, plate badge (if provided)
2. **💰 Preços** — FIPE, média mercado, faixa min/max, % vs FIPE
3. **⚙️ Especificações Técnicas** — CV (highlighted green), torque, motor, câmbio, consumo cidade/estrada
4. **📋 Anúncios Webmotors** — up to 5 listing cards (title, km, city, price)
5. **🏆 Veredito** — badge + justification
6. **"📷 Nova Análise"** button → `/auto`

---

## Tab 3 — Moda (👗)

### Capture Screen (`/fashion`)

Standard `CameraButton` with `capture="environment"`. Label: "Fotografe a peça ou acessório". No extra fields.

On capture: saves base64 to `sessionStorage` (`buscapp_fashion_image`), navigates to `/fashion/analyzing`.

### Analyzing Screen (`/fashion/analyzing`)

Cycling messages:
- "Identificando a peça..."
- "Analisando marca e modelo..."
- "Verificando sinais de autenticidade..."
- "Buscando preços oficiais..."
- "Consultando mercado premium..."
- "Montando relatório..."

Calls `POST /api/fashion/analyze` with `{ imageBase64 }`.

### API Route — `/api/fashion/analyze`

**Step 1 — Identify + authenticity (Claude Vision):**  
Single call to `claude-sonnet-4-6`. Extract identification AND authenticity signals in one pass:
```json
{
  "brand": "Nike",
  "item": "Tênis",
  "model": "Air Jordan 1 Retro High OG",
  "colorway": "Chicago",
  "year": "2019",
  "category": "Footwear",
  "authenticityScore": 82,
  "signals": [
    { "status": "ok", "detail": "Costura lateral uniforme e precisa" },
    { "status": "ok", "detail": "Swoosh posicionado corretamente" },
    { "status": "warning", "detail": "Etiqueta interna não visível na foto" },
    { "status": "fail", "detail": "Logotipo com espaçamento irregular" }
  ]
}
```
`status` values: `"ok"` → ✅, `"warning"` → ⚠️, `"fail"` → ❌

**Step 2 — Web search (Tavily):**  
3 parallel queries:
- `"[brand] [model] [colorway] preço oficial brasil site"`
- `"[brand] [model] farfetch stockx preço"`
- `"[brand] [model] [colorway] original vs fake como identificar"`

**Step 3 — Synthesize prices (Claude):**  
Extract market prices per platform:
```ts
{
  platforms: Array<{ name: string, price: string, currency: "BRL" | "USD" }>
}
```

**Final response shape:**
```ts
{
  item: { brand, model, colorway, year, category, itemType },
  authenticity: {
    score: number,           // 0–100
    verdict: "ORIGINAL" | "SUSPEITO" | "RÉPLICA",
    signals: Array<{ status: "ok"|"warning"|"fail", detail: string }>
  },
  prices: {
    platforms: Array<{ name: string, price: string, currency: string }>
  }
}
```

**Score → verdict mapping:** ≥70 → ORIGINAL (green), 40–69 → SUSPEITO (amber), <40 → RÉPLICA (red)

### Report Screen (`/fashion/report`)

Sections in order:
1. **Item ID card** — brand, model, colorway, year, category
2. **🔍 Score de Autenticidade** — percentage bar (color matches verdict), label
3. **Sinais Observados** — list with ✅ ❌ ⚠️ per signal
4. **💰 Preço de Mercado** — one row per platform (name + price)
5. **🏆 Veredito** — ORIGINAL / SUSPEITO / RÉPLICA badge with color + justification
6. **"📷 Nova Análise"** button → `/fashion`

---

## Shared Infrastructure

### Types (`lib/types.ts`)
Add:
- `VehicleAnalysis` — full auto report shape
- `FashionAnalysis` — full fashion report shape

### Storage (`lib/storage.ts`)
Add `saveVehicleAnalysis` / `getVehicleHistory` and `saveFashionAnalysis` / `getFashionHistory` — same localStorage pattern as existing, separate keys (`buscapp_auto_history`, `buscapp_fashion_history`).

### Tab Bar Component (`components/TabBar.tsx`)
New shared component. Receives `activeTab: "camera"|"upload"|"auto"|"fashion"`. Renders 4 tabs with icons. Hidden on analyzing/report pages.

### Layout
`app/layout.tsx` does NOT wrap children in the tab bar globally (report/analyzing pages exclude it). Each capture page renders `<TabBar>` directly.

---

## What Is NOT Changing

- `/api/analyze` — untouched
- `/analyzing`, `/report`, `/history` — untouched  
- `lib/claude.ts`, `lib/tavily.ts`, `lib/storage.ts` — extended, not rewritten
- Design system (colors, fonts, card styles) — unchanged

---

## File Map

```
buscapp/
  app/
    upload/page.tsx              (new — capture screen)
    auto/
      page.tsx                   (new — capture + plate field)
      analyzing/page.tsx         (new)
      report/page.tsx            (new)
    fashion/
      page.tsx                   (new — capture screen)
      analyzing/page.tsx         (new)
      report/page.tsx            (new)
    api/
      auto/analyze/route.ts      (new)
      fashion/analyze/route.ts   (new)
  components/
    TabBar.tsx                   (new)
    AuthenticityBar.tsx          (new — score bar for fashion)
  lib/
    types.ts                     (extend)
    storage.ts                   (extend)
```

Total: **10 new files**, **2 files extended**.
