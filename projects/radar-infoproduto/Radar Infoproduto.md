---
type: project
name: "Radar Infoproduto"
status: "em andamento"
owner: "[[Guilherme Figueredo]]"
started: 2026-08-14
tags:
  - project/radar-infoproduto
  - project/active
---

# Radar Infoproduto

## Description

Script que encontra infoprodutos validados rodando na Europa e no Reino Unido,
ranqueados por evidência de lucro, para [[Guilherme Figueredo]] **modelar** uma
oferta própria em euro.

O sinal central é longevidade de anúncio: uma oferta que paga mídia há meses
está lucrando. A API pública da Ad Library da Meta expõe esse dado — mas só para
anúncio entregue na UE e no Reino Unido, por obrigação do DSA. Anúncio dos EUA
não sai por API, o que inverte a intuição do pedido original: **a Europa é a
metade aberta**.

Design completo e aprovado em `2026-08-14-radar-infoproduto-design.md`.

## Key Decisions

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-08-14 | Objetivo é modelar, não promover como afiliado | Guilherme quer construir a oferta dele, não vender a dos outros |
| 2 | 2026-08-14 | Só Meta Ad Library API no v1 | Única fonte com API oficial, gratuita e estável. TikTok não tem API; ClickBank não tem API pública de marketplace |
| 3 | 2026-08-14 | EUA fora do v1 | A API só devolve anúncio comercial para UE e Reino Unido. Cobrir EUA exigiria raspagem bloqueada ou ferramenta paga |
| 4 | 2026-08-14 | Histórico em JSON versionado, não SQLite | O vault viaja por git entre máquinas; binário gitignorado divergiria |

## Current Risks & Blockers

| # | Risk/Blocker | Severity | Status |
|---|-------------|----------|--------|
| 1 | Verificação de identidade na Meta pode travar ou demorar dias | Alta | Open — é o primeiro passo e é humano; plano B é antecipar o coletor do ClickBank |
| 2 | **Construir isto em vez de vender o [[Atendente IA]]** | Alta | Open — o radar não gera receita; a meta de 13/09/2026 continua sendo abordagens |
| 3 | Termos em inglês podem trazer pouco volume na UE continental | Média | Open — medir na primeira rodada |

## Estado da construção (15/08/2026)

O v1 está **construído e testado**, na branch `feat/radar-infoproduto`. Falta
só rodar contra a API de verdade, o que depende do token.

| Módulo | O que faz |
|---|---|
| `scripts/radar_infoproduto.py` | CLI: `--date`, `--force`, `--render-only`, bootstrap de venv |
| `radar/config.py` | Países, termos, listas de domínio, pesos e limiares |
| `radar/meta_client.py` | Único módulo com rede: paginação, retry, guarda de países |
| `radar/classify.py` | É infoproduto? é lusófono? |
| `radar/offers.py` | Anúncios → ofertas + score + portão de maturidade |
| `radar/store.py` | Histórico JSON e diff entre rodadas |
| `radar/render.py` | Nota markdown da rodada |

87 testes passando, todos offline contra fixture. Nenhum toca a rede.

**Bugs encontrados em review que teriam chegado na nota semanal:**

1. `snapshot_urls` devolvia os 5 criativos mais **velhos** em vez dos mais
   recentes — links para anúncio possivelmente já parado
2. A guarda de países era **inerte**: comparava a config com ela mesma e nunca
   podia disparar, justamente contra a falha que o spec chama de traiçoeira
3. O campo `countries` nunca chegaria — `FIELDS` não pedia o dado
4. Termo composto casava atravessando dois campos de copy ("Join the free" +
   "training now" virava "free training")
5. `history.json` corrompido por conflito de merge do git cuspia traceback cru

## Notes

Nasceu na conversa de 14/08/2026, no mesmo dia em que o plano do
[[Atendente IA]] foi travado. A relação entre os dois projetos precisa ficar
explícita: o [[Atendente IA]] é a operação de receita de 30 dias; o Radar é
pesquisa de mercado para a decisão *seguinte*. Se os dois competirem por tempo,
o [[Atendente IA]] ganha.

## Tarefas

- [x] Revisar e aprovar o spec de design ✅ 2026-08-14
- [x] Escrever o plano de implementação ✅ 2026-08-14
- [x] Construir o v1 (Tasks 2 a 13, 87 testes) ✅ 2026-08-15
- [x] Painel acumulado (`Painel.md`, reescrito a cada rodada) ✅ 2026-08-15
- [x] Review final e merge na main, com push ✅ 2026-08-15
- [ ] Criar app de desenvolvedor na Meta e passar pela verificação de identidade 📅 2026-08-18 #task
- [ ] Task 1 do plano: sondar a API na mão e confirmar versão, `search_type` e a forma de `total_reach_by_location` 📅 2026-08-18 #task
- [ ] Primeira rodada real e auditoria manual do top 20 📅 2026-08-19 #task
- [ ] Documentar o script em `docs/reference/scripts.md` (bloqueado: o arquivo tem alteração pendente do dono) 📅 2026-08-19 #task

---
**See also:** [[Atendente IA]] | [[Guilherme Figueredo]]
