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

## Painel (pronto em 05/08/2026)
Projeto Lovable **"Co-Piloto TikTok"** — id `558553c9-7d94-4a6c-a282-fb8828387ac0`,
workspace `vVCbLWo6thE41wKRMQww` ("Guilherme's Lovable"). Está sob a conta
`sergiogpn@gmail.com`, mas no workspace do Guilherme — a preocupação antiga de
conta foi resolvida assim.

Construído em 8 etapas: esqueleto → auth Supabase (email/senha, rotas
protegidas) → página Ao Vivo (3 colunas, Realtime em `messages`/`leads`, fila de
resposta) → bloco de coaching → página Lives Prontas + faixa de supervisão →
multiconta (`sellers`/`seller_users`/`produtos`/`frete_regras`/
`base_conhecimento`/`configuracoes`) + tela de Configurações → importação de
planilha CSV/XLSX na aba Produtos → rebrand para Livewire.

Banco no **Lovable Cloud** (Supabase gerenciado), 12 tabelas + view
`lives_ranking` + funções `upsert_lead`, `tem_acesso`, trigger
`aplicar_comando_supervisao`. Já com dados de seed da Mix Conecta.

## Status do agente (06/08/2026)
- Código agora vive **dentro do vault**, em `tiktok-copilot/` (commit `99487b1`).
  O `.env` está no `.gitignore` — a service_role nunca entra no git.
- GitHub: repo **privado** em `guilhermeamorim123/tiktok-copilot`, branch `main`.
  Identidade correta do projeto: `Guilherme <guiafiguerdo@gmail.com>`.
- **Agente sincronizado com o banco (06/08/2026):** catálogo, frete e base de
  conhecimento saem das tabelas `produtos`/`frete_regras`/`base_conhecimento`;
  auto-resposta, teto/min, intents, tom de voz e threshold de lead quente saem
  de `configuracoes`. `products.json` e `.env` viraram fallback do modo sqlite.
  Refresh a cada 30s durante a live, `live_id` nas mensagens, `schema.sql`
  regerado a partir do banco real.
- Decisões que valem lembrar: catálogo vazio **aborta o arranque** (não entra na
  live respondendo "não sei"); o refresh só mexe no interruptor quando o valor
  muda no banco, para não desfazer um PARAR TUDO; nem o painel consegue liberar
  `reclamacao` para auto-envio.
- Falta: módulo RTMP/OBS do replay (comando `replay_live` volta `failed`),
  vendas/receita (dependem do TikTok Shop), `viewers_pico`/`viewers_media`
  (ingest só escuta comentários), cobrança.
- **Dívida do multi-tenant:** `seller_id` ainda tem `default 'mix-conecta'` nas
  tabelas de operação. Derrubar antes de entrar a segunda loja (comando no
  rodapé do `schema.sql`).
- **Este Mac não roda o agente:** só tem Python 3.9 do sistema, sem Homebrew, e
  o código exige 3.10+. Testes foram rodados com um shim de dataclass em
  scratchpad. Para rodar de verdade aqui, instalar Python 3.11+.
- Próximo passo: pegar URL + service_role do Lovable Cloud, pôr no `.env` com
  `STORE_BACKEND=supabase`, cadastrar os produtos reais no painel e rodar live
  de teste com a auto-resposta desligada.
