---
name: project-clientia
description: App CLIENTIA — substituto do Outops SAC, pós-venda + pré-venda ML com IA respondendo automaticamente. Stack, credenciais, estado atual e problemas resolvidos.
metadata:
  type: project
---

App de pós-venda e pré-venda para Mercado Livre, criado no Lovable.dev.
URL de produção: https://clientiamix.lovable.app
GitHub: repo privado (credenciais nas Lovable Secrets — NUNCA commitar)

**Why:** O app anterior (Outops) foi banido do Lovable por "Deceptive Behaviors" (referência explícita ao Mercado Livre no nome/textos). CLIENTIA usa terminologia neutra: Clinta = ML, Atendimento = SAC.

**Stack:** TanStack Start + React 19 + Vite + Tailwind v4 + shadcn/ui + Supabase + Anthropic Claude (claude-sonnet-4-5-20250929) via @ai-sdk/anthropic + pg_cron (sync a cada 2 min).

**Lovable project ID:** df990ab7-a9ba-4859-857d-a618ae968984 (conta diferente do MCP — dá 403 via MCP)

**ML OAuth credenciais (Lovable Secrets):**
- Client ID: 2280023910287430
- Secret: P6Wwf750gLue3odpUNJTOnLecOdxLkTh

**Cron:** pg_cron chama /api/public/cron/sync a cada 2 min com header X-Cron-Secret. Chave aleatória: X7k#mP2$qL9vNw4Rj8sYt3uBdE6cFhZ

**Tabelas principais:** marketplace_accounts, conversas, conversa_mensagens, atendimento, devolucoes, entregas_agradecidas, base_conhecimento

**How to apply:** Ao retomar trabalho no CLIENTIA, lembrar que:
1. Lovable MCP dá 403 — user precisa digitar mensagens manualmente no editor Lovable
2. Lovable NÃO puxa do GitHub — só empurra. Código no GitHub ≠ código deployado
3. Créditos Lovable são escassos — preparar mensagem única e precisa antes de enviar
4. O cron roda a cada 2 min — mudanças de código são testadas aguardando o próximo ciclo

**Estado em 2026-06-22:**
- Auto-resposta IA (pré-venda): DEPLOYADA — src/lib/ai.server.ts criado + runSync processa conversas pendentes
- Confidence threshold: 0 (responde TUDO)
- Anthropic API Key nova (chave anterior sk-ant-api03-BvLeoqANf28t_... foi comprometida — revogar se ainda ativa)
- Conta conectada: MIXCONECTA. Pendente conectar: MIMI20240104142003, CS20250912133322
- 10 conversas pendentes → devem ser respondidas no próximo cron após deploy de 2026-06-22

**Bugs resolvidos:**
- Endpoint reclamações ML: /post-purchase/v1/claims/search (não /claims/search)
- OAuth salvando account_id errado (fallback) → corrigido para tokenResponse.user_id
- RLS bloqueando 28 linhas de atendimento → fix direto SQL
- Cron apontando para preview URL → redirecionado para produção
- stack depth limit exceeded (RLS recursion) → corrigido pelo Lovable
- Chave fechando bloco for (pre-sale questions) faltando → corrigido pelo Lovable junto com ai.server.ts
