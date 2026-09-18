---
name: project-outsell
description: OutSell — SaaS de prospecção local (concorrente do Zuzyia) nascido do DGX Foco. Decisões do brainstorming de 2026-09-17, stack, motor Serper, 4 subprojetos.
metadata:
  type: project
---

OutSell é o SaaS que remodela o DGX Foco (Lovable `879efa46-428c-44f0-9ac7-ff28443fc046`, workspace do Sergio) num produto vendável, concorrente direto do Zuzyia (zuzyia.com.br: criador de site por IA + prospecção "sem site" + contrato + dashboard + mentor IA, R$ 169/mês ou R$ 249 vitalício).

**Decidido em 2026-09-17 (brainstorming):**
- Pacote completo em 4 subprojetos, ordem 1 → 2 → 4 → 3: (1) Núcleo de prospecção, (2) Fechamento (contrato, avaliador de preço, dashboard), (3) Criador de site por IA, (4) Plataforma (assinatura, landing, mentor IA).
- Nome: OutSell. Marca visual: Outsell OPS Design Hub (Lovable `35282fc2-b6d2-4697-b684-cd74bab3de23`), claro, azul #1A56DB, Inter. Só o ícone do logo, sem nome (Guilherme vai mandar o arquivo).
- Código: repo `outsell` no GitHub, Next.js 15 + Tailwind v4 + shadcn + Supabase, deploy Vercel. Reescrita (não evolução do TanStack Start do DGX Foco).
- Motor de busca: Serper.dev (Maps), chave da casa, custo embutido no plano. Google Places rejeitado por custo/BYOK; busca via Anthropic rejeitada (US$ 10/1k, sem listagem estruturada). Claude só pra IA em cima dos dados.
- Frentes: Sem site e Revenda com peso igual (escolha do dono; brief alertava diluição).
- Telas: Stitch só pra direção visual (3 prompts no spec); tudo construído em código.

**Spec:** `docs/superpowers/specs/2026-09-17-outsell-nucleo-design.md`

**Why:** Guilherme quer um SaaS vendável a partir do que a DGX já construiu, sem ficar refém de crédito do Lovable nem de custo variável do Google.

**How to apply:** Ao retomar, ler o spec antes de qualquer código. Próximo passo após aprovação do spec: `writing-plans` pro subprojeto 1. Guilherme prefere telas de nível alto ("muito fodas") e decisões rápidas em multiple choice.
