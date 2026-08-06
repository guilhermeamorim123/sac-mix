---
name: project-livewire
description: Livewire — SaaS co-piloto de IA para vendedores de live commerce, com painel em tempo real, coaching, respostas automáticas e CRM integrado
metadata:
  type: project
---

Guilherme quer construir um SaaS chamado **Livewire** — AI co-pilot para vendedores de live commerce.

**Nome definido em 05/08/2026.** Regra: nunca usar TikTok/Tik/Tok na marca — a
ByteDance protege com rigor, e prender o nome a uma plataforma fecharia a porta
para live do Instagram e Shopee. Livewire colide com o framework Laravel
Livewire, mas em categoria diferente: custa ranqueamento no Google, não risco de
marca. Aceito porque a aquisição é social (Instagram/indicação), não busca.
Wingman foi a segunda opção, descartada por colidir com produto de IA de vendas
(Wingman/Clari) — mesma categoria, risco real de marca.
Falta checar: `.com`, `.com.br`, @ no Instagram e busca no INPI.

**Why:** Primeiro uso interno na Mix Conecta para validar, depois escalar como SaaS para outros lojistas a R$60/mês. Meta: 3.000 clientes = R$180k/mês.

**How to apply:** Quando o usuário mencionar o app de TikTok Lives, retomar esse contexto completo e continuar de onde parou.

## Funcionalidades definidas

| Funcionalidade | Decisão |
|---|---|
| Leitura do chat TikTok Live em tempo real | ✅ incluir |
| Respostas automáticas (perguntas simples: preço, frete, prazo) | ✅ incluir |
| Sugestão com 1 clique pro vendedor (perguntas complexas) | ✅ incluir |
| Alertas de leads quentes no painel | ✅ incluir |
| Captura automática de WhatsApp/números do chat → CRM | ✅ incluir |
| CRM integrado no app | ✅ incluir |
| TikTok Shop integrado (produtos, preços, links) | ✅ incluir |
| Recomendação de melhores horários pra live | ✅ incluir |
| Coaching em tempo real pro vendedor | ✅ incluir |
| Loop de vídeo gravado como live falsa | ✅ **revertido em 04/08/2026** — Guilherme decidiu incluir, ciente do risco de ban. Vira a página "Lives Prontas" (biblioteca de lives gravadas ~1h/1h20, com nota boa/regular/ruim, vendas/hora e recomendação de reexibir). Exige check-in de supervisor. |

## Modelo de resposta (híbrido)
- Perguntas simples e repetidas → AI responde automaticamente no chat
- Perguntas complexas / leads quentes → AI sugere, vendedor aprova com 1 clique
- Sempre orientar vendedor a parecer presente na live

## Stack definida (04/08/2026)
- Agente local: Python — roda no PC do vendedor (websocket e Playwright não rodam no navegador)
- Chat da live: biblioteca TikTokLive (não-oficial)
- IA: Claude API (`claude-opus-5`), classificação em lote com cache do catálogo
- Ponte: Supabase (Realtime + RLS multi-tenant)
- Painel: Lovable (React/Vite/Tailwind/shadcn)
- Envio no chat: Playwright sobre o LIVE Center — **não existe API oficial de envio**
- TikTok Shop: adiado, exige aprovação de partner app (semanas)

## Status
- Código em **`C:\dev\tiktok-copilot`** (repo git próprio, fora do vault).
  Ficou fora do OneDrive de propósito: o `.env` guarda a service_role do Supabase,
  e Desktop e Documentos estão os dois redirecionados para o OneDrive.
- GitHub: repo **privado** em `guilhermeamorim123/tiktok-copilot`, branch `main`.
  Identidade correta do projeto: `Guilherme <guiafiguerdo@gmail.com>`.
- **Atenção com contas:** o conector do Lovault/Lovable e o Google desta máquina
  estão em `sergiogpn@gmail.com`, que **não** é a conta que Guilherme quer usar.
  A conta certa é a do GitHub (`guilhermeamorim123`). Reconectar o Lovable pelo
  claude.ai antes de criar o painel — não dá para trocar isso pelo Claude Code.
- Falta: módulo RTMP/OBS do replay, vendas/receita (dependem do TikTok Shop), cobrança
- Próximo passo: preencher `products.json` real e rodar live de teste com
  `AUTO_REPLY_ENABLED=false`
