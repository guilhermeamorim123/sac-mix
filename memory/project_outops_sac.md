---
name: project-outops-sac
description: Sistema SAC Outops — arquitetura, bugs corrigidos e estado atual do debugging
metadata:
  type: project
---

# Projeto Outops — SAC Inteligente

**Repo:** https://github.com/guilhermeamorim123/outops.git  
**App:** https://outops.lovable.app/  
**Stack:** TanStack Start + React 19 + Supabase + Tailwind v4 + Vercel AI SDK  
**Construído em:** Lovable.dev (gerador de apps com IA)

## Arquitetura principal

- `pos_venda` table — casos de atendimento pós-venda (reclamações, devoluções, trocas, dúvidas). `seller_id` = auth `user_id`
- `returns` table — fluxo físico de inspeção de devoluções (fotos, supervisor, reposição). `seller_id` = `ml_accounts.id` (UUID da conta ML, diferente do user_id!)
- `ml_accounts` table — contas ML conectadas (multi-conta). Token armazenado aqui para funções novas.
- `sellers` table — LEGADO, tokens antigos. Usado por `mlJSON()` (deprecated)

## Funções de sync (todas em auto-resposta.ts)

O cron unificado é `POST /api/public/ml/auto-resposta`. Executa para cada conta ML:

| Função | O que faz | Tabela destino |
|--------|-----------|----------------|
| `processAccount` | Responde perguntas pré-venda com IA | `conversations`, `messages` |
| `syncMLPosVenda` | Sync claims+returns via `sellers` (LEGADO) | `pos_venda` |
| `processarMensagensPosVenda` | Processa mensagens de packs pós-venda | `pos_venda` |
| `syncMLClaimsToReturns` | Importa claims para inspeção física | `returns` |
| `syncPosVendaFromML` | Importa claims abertos para atendimento | `pos_venda` |
| `enviarMensagensEntrega` | Envia msg de agradecimento pós-entrega | `delivery_messages` |
| `fixProductTitles` | Backfill de títulos de produto | `returns` |

## Bugs corrigidos (sessão jun/2025)

### Bug 1 — syncPosVendaFromML usava endpoint errado
**Arquivo:** `src/routes/api/public/ml/auto-resposta.ts`  
**Função:** `syncPosVendaFromML`  
**Erro:** endpoint `/claims/search?seller_id=...&seller_role=seller&status=opened` retornava 404  
**Fix:** trocado para `/post-purchase/v1/claims/search?seller_id=...&stage=claim&status=opened`  
**Por que funcionou para devoluções mas não para reclamações:** `syncMLClaimsToReturns` já usava o endpoint correto `/post-purchase/v1/claims/search`

### Bug 2 — responsavel: "ia" inválido
**Erro:** `invalid input syntax for type uuid: "ia"` — campo `responsavel` espera UUID ou null  
**Fix:** linha `responsavel: "ia"` removida do insert em `syncPosVendaFromML`

### Bug 3 — tipo hardcoded como "reclamacao"
**Fix:** `tipo: claim.type === "return" ? "devolucao" : "reclamacao"` (dinâmico)

## Estado atual (jun/2025)
- Fix aplicado no Lovable, aguardando confirmação do sync funcionando
- 3 contas ML conectadas: MIMI20240104142003, MIXCONECTA, CS20250912133322
- `pos_venda.claims: 20` por conta — o endpoint `/post-purchase/v1/claims/search` está retornando dados
- Erros pendentes não relacionados ao bug principal:
  - `pos_venda_mensagens` — endpoint `/messages/packs?tag=post_sale` retorna 404 (problema separado)
  - `entrega` — filtro `order.status=delivered` inválido (problema separado)

## Como testar o sync manualmente

```powershell
(Invoke-WebRequest -Uri "https://outops.lovable.app/api/public/ml/auto-resposta" -Method POST).Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Olhar campo `pos_venda_claims.imported` — deve ser > 0 na primeira execução após o fix.

**Why:** Guilherme usa Lovable para editar o código e não tem acesso fácil ao git/IDE  
**How to apply:** Sempre gerar prompt direto para colar no chat do Lovable com localização exata do código
