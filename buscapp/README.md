# BUSCAPP

PWA mobile de análise de produtos para revendedores. Fotografe qualquer produto e receba em segundos:

- Preços no mercado (ML, Amazon, Shopee)
- Volume de vendas e nível de concorrência
- Tendência do produto
- Margem estimada e lucro por unidade
- Veredito: VALE INVESTIR / ATENÇÃO / NÃO VALE

## Setup local

1. `npm install`
2. Copiar `.env.example` → `.env.local` e preencher as chaves
3. `npm run dev`
4. Abrir `http://localhost:3000`

## Variáveis de ambiente

| Variável | Onde obter |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `TAVILY_API_KEY` | app.tavily.com (free tier: 1.000 req/mês) |

## Deploy (Vercel)

```bash
npm i -g vercel
vercel
vercel env add ANTHROPIC_API_KEY
vercel env add TAVILY_API_KEY
vercel --prod
```

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS (design system preto + verde)
- Claude Vision (identificação do produto)
- Tavily Search (6 buscas paralelas)
- localStorage (histórico no device)
- PWA — installable no iPhone via Safari
