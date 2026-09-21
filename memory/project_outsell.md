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

**Estado em 2026-09-18 (fim da sessão 1 de execução):**
- Plano: `docs/superpowers/plans/2026-09-17-outsell-nucleo.md` (26 tasks, pasta gitignored, só local). Design doc compartilhável: https://claude.ai/code/artifact/068eddeb-c622-4357-b2cf-8db08b9e26e8
- Repo: `C:\Users\Dvilh\dev\outsell` → github.com/guilhermeamorim123/outsell (privado, main). Stack real: **Next 16.3.5** (middleware virou `src/proxy.ts`), React 19.2, Tailwind 4, **shadcn 4.21 sobre Base UI** (props `onCheckedChange`/`onOpenChange`/`onValueChange` iguais, mas `data-checked` em vez de `data-state`), Vitest 5 (`vitest.config.mts`), Playwright config já criado (0 testes até Task 25).
- Task 1 DONE e aprovada nas duas revisões (commit c64a675).
- Tasks 2–7 (lógica pura) despachadas num único subagente na noite de 2026-09-17; ao retomar, checar `git log` do repo e rodar `npm test`; depois revisar (spec + qualidade) e seguir pra Task 8.
- Supabase: projeto `outsell` criado via MCP na org Mixconecta (ref `iwiknbvwhtbmrnqpyawp`, sa-east-1, free). Migração `core` e seed `limites_plano` (18 linhas) JÁ APLICADOS pelo MCP. Falta: gravar `supabase/migrations/0001_core.sql`, `supabase/seed.sql` e `src/lib/supabase/types.ts` no repo (tipos geráveis de novo com `generate_typescript_types` via MCP). `.env.local` do repo já tem URL + chave publishable.
- Pendente do Guilherme: SERPER_API_KEY, ANTHROPIC_API_KEY, SUPABASE_SERVICE_ROLE_KEY (painel → API), e o arquivo do logo Outsell OPS (só o ícone; ele mostrou a imagem no chat, precisa salvar em `+Inbox/`). Chaves ele disse que passa no final.
- Fluxo de execução: subagent-driven (implementador + revisor de spec + revisor de qualidade por task/bloco). Agrupar tasks pequenas é aceitável.

**Estado em 2026-09-18 (sessão 2, manhã):**
- Fase 1 (Tasks 2–7) revisada e aprovada após 2 rodadas de correção (bug crítico em `normalizarE164` fechado; `calcularScore` virou 1 argumento com união discriminada; `textoDetalhe(d)`; `texto.ts`, `score/pontos.ts`).
- Tasks 8–9 aprovadas. Migrações aplicadas via MCP e versionadas no repo: `0001_core`, `0002_hardening` (devolver_consultas só service_role com `_user`, revokes em helpers, search_path, seed de limites), `0003_perfis_grants` (usuário NÃO edita plano/plano_ate; só nome/tipo_negocio/onboarding). `seed.sql` removido. Next 16: guarda de rota é `src/proxy.ts` (401 JSON em /api). `caminhoSeguro()` em `src/lib/seguranca.ts`.
- Lição SQL: REVOKE de coluna não subtrai grant de tabela; tem que revogar a tabela e conceder colunas.
- Supabase Auth está exigindo confirmação de e-mail → pedir ao Guilherme pra desligar "Confirm email" no painel (Authentication → Providers → Email) pra testar; ou usar SMTP próprio.
- Tasks 10–11 (Serper provider + rota /api/varreduras) despachadas; depois 12–14, depois UI (15–23).
- Ainda faltam do Guilherme: SERPER_API_KEY, ANTHROPIC_API_KEY, SUPABASE_SERVICE_ROLE_KEY (painel → Settings → API → service_role), logo em `+Inbox/`.

**Estado em 2026-09-19 (pausa por limite do plano Max):**
- Backend completo e aprovado: Tasks 1–14 + follow-ups (commit `c46711e`, 218 testes). Migrações aplicadas e versionadas: 0001 core, 0002 hardening, 0003 perfis_grants, 0004 cota_varredura (consumir_cota_varredura atômica, devolver_varredura, leads_existentes). Inserts de lead usam `inserirLeadsComFallback` (bisseção, sem upsert em índice parcial).
- UI lote 1 (Tasks 15–17: tokens, shell, componentes, onboarding, conta, campanhas) aprovado (commit `14795c0`). lucide sem `Instagram` → `AtSign`. Base UI usa `render` em vez de `asChild`.
- UI lote 2 (Tasks 18–20: captar, leads, disparar + `requireUser()` em `src/lib/auth.ts`, `chamarApi` em `src/lib/cliente-api.ts`) foi DESPACHADO e pode ter ficado pela metade quando a sessão parou. Ao retomar: `git log`/`git status` no repo; se houver commits parciais, checar gates (`npm test`, `tsc`, `lint`, `build`) e concluir o que faltar (ver prompt do lote 2 = plano Tasks 18–20 adaptado às respostas das APIs).
- Depois: lote 3 (Tasks 21–23: pipeline, templates, início), depois Tasks 24–26 (cron, E2E, CI/Vercel). Modo econômico: 1 revisão combinada por lote, revisor Sonnet.
- Vercel: time `team_EnJo1ihShZyi9KqQVKqVQP1s` (conta do Sergio). `create_git_project` falha com repo_not_found até o Guilherme liberar o GitHub App da Vercel pro repo `guilhermeamorim123/outsell`. Depois: criar projeto, envs `NEXT_PUBLIC_SUPABASE_URL=https://iwiknbvwhtbmrnqpyawp.supabase.co`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ElVi75S88lxNM0dZ2RgpvQ_yf2hEFOK`, e adicionar o domínio Vercel em Supabase Auth → URL configuration.
- Pendências do Guilherme: liberar GitHub App na Vercel; desligar "Confirm email" no Supabase Auth; chaves SERPER/ANTHROPIC/SUPABASE_SERVICE_ROLE; logo em `+Inbox/`.
- Máquina com pouca RAM (8 GB): gates rodam melhor pelo PowerShell; nunca deixar `next dev` aberto.

**Estado em 2026-09-20 — NÚCLEO COMPLETO (26/26 tasks), commit `791c78b`, 226 testes, lint/tsc/build limpos.**
- Telas: shell, onboarding, conta, campanhas (lista + nova), captar (+ prévia/import), leads (virtualizada + sheet + planilha), disparar (fila com atalhos + IA), pipeline (kanban), templates, início (painel). Cron `/api/cron/limpeza` (vercel.json, gru1), CI GitHub Actions, E2E Playwright (3 specs; rodam só com Supabase sem "Confirm email"), README pt-BR.
- Convenções que valem pro subprojeto 2+: `requireUser()` no topo das pages; `chamarApi` no cliente; ações do servidor devolvem `{ok, erro?}`; erros de API genéricos com `ref`; React Compiler lint (sem setState síncrono em effect); Base UI `render` prop; lucide sem ícones de marca.
- DEPLOY PENDENTE: Vercel `create_git_project` falha com repo_not_found até o Guilherme liberar o GitHub App da Vercel (conta Vercel do Sergio, team `team_EnJo1ihShZyi9KqQVKqVQP1s`) pro repo `guilhermeamorim123/outsell`. Depois: criar projeto, envs (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ElVi75S88lxNM0dZ2RgpvQ_yf2hEFOK, SUPABASE_SERVICE_ROLE_KEY, SERPER_API_KEY, ANTHROPIC_API_KEY, CRON_SECRET), Supabase Auth → URL configuration com o domínio Vercel, desligar Confirm email.
- Próximos subprojetos (specs próprias): 2 Fechamento (contrato, avaliador de preço, dashboard de vendas), 4 Plataforma (Kiwify/Stripe, landing, mentor IA), 3 Criador de site.
- Ainda pendente do Guilherme: logo em `+Inbox/` (trocar `src/components/shell/logo.tsx`), chaves, Vercel GitHub App, Confirm email.

**Infra definitiva (2026-09-20):**
- Supabase OFICIAL do OutSell: projeto `outsell` ref `grqjopupgrkpgzzblxsm` na org do Guilherme (`guilhermeamorim123's Org`, `lmszghbwqocdicqpjivn`), sa-east-1, free. URL `https://grqjopupgrkpgzzblxsm.supabase.co`, publishable `sb_publishable_SdxFGkDjuetLECa-zjEx5w_xBUKM1aL`. Migrações 0001–0004 aplicadas via MCP em 2026-09-20 e verificadas. Conector Supabase do claude.ai agora autenticado na conta do Guilherme.
- O projeto antigo `iwiknbvwhtbmrnqpyawp` (org Mixconecta, conta do Sergio) ficou ÓRFÃO: pausar/apagar quando conveniente.
- Vercel: projeto `outsell` na conta pessoal do Guilherme (guiafiguerdo@gmail.com, time "guilherme-amorim-figueredo-s-projects"), produção `https://outsell-alpha.vercel.app`, Hobby, Fluid compute, Node 24. Meu conector Vercel NÃO enxerga essa conta (só o time do Sergio): configuração de envs/cron é manual pelo Guilherme. Primeiro deploy deu 500 por falta de envs.
- `.env.local` local já aponta pro projeto novo.

**Landing integrada (2026-09-21), branch `feat/landing` (commit `bfb21dd`, push feito, preview Vercel automático):**
- Landing (HTML feito pelo Guilherme no v0) vive em `src/app/(landing)/` com layout raiz próprio (sem Tailwind, Google Fonts Barlow); screenshots byte a byte iguais ao original em 1440/390px. App inteiro passou pro route group `src/app/(app)/`; dashboard agora é `/painel`; `/` é pública e o proxy manda logado pra `/painel`.
- Links da landing: `/entrar`, `/entrar?modo=criar`, planos `/entrar?modo=criar&plano=radar|rota|territorio` (guardado como `plano_interesse` na metadata do signup). Assets em `public/logo.png` e `public/favicon.png`; shell usa o ícone real.
- Pendente: Guilherme conferir o preview e fazer merge em `main` (produção). Textos de plano ainda têm `[X]` (placeholders do original). O projeto separado da landing na Vercel pode ser apagado depois do merge.
