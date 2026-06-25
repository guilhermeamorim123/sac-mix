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
