export type SalesVolume = 'Alto' | 'Médio' | 'Baixo'
export type CompetitionLevel = 'Alta' | 'Média' | 'Baixa'
export type Trend = 'Em Alta' | 'Estável' | 'Em Queda'
export type RiskLevel = 'Alto' | 'Médio' | 'Baixo'
export type VerdictRating = 'VALE INVESTIR' | 'ATENÇÃO' | 'NÃO VALE'

export interface ProductInfo {
  name: string
  brand: string
  model: string
  category: string
}

export interface PriceInfo {
  min: number
  avg: number
  max: number
  platforms: string[]
}

export interface MarketInfo {
  salesVolume: SalesVolume
  competition: CompetitionLevel
  trend: Trend
  reviewSummary: string
}

export interface InvestmentInfo {
  suggestedPrice: number
  marginPercent: number
  profitPerUnit: number
  riskLevel: RiskLevel
}

export interface Verdict {
  rating: VerdictRating
  justification: string
}

export interface SimilarProduct {
  name: string
  note: string
}

export interface ProductAnalysis {
  id: string
  createdAt: string
  imageBase64?: string
  product: ProductInfo
  prices: PriceInfo
  market: MarketInfo
  investment: InvestmentInfo
  verdict: Verdict
  similarProducts: SimilarProduct[]
}

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
