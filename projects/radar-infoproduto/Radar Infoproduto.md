---
type: project
name: "Radar Infoproduto"
status: "planejamento"
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

## Notes

Nasceu na conversa de 14/08/2026, no mesmo dia em que o plano do
[[Atendente IA]] foi travado. A relação entre os dois projetos precisa ficar
explícita: o [[Atendente IA]] é a operação de receita de 30 dias; o Radar é
pesquisa de mercado para a decisão *seguinte*. Se os dois competirem por tempo,
o [[Atendente IA]] ganha.

## Tarefas

- [ ] Criar app de desenvolvedor na Meta e passar pela verificação de identidade 📅 2026-08-15 #task
- [ ] Revisar e aprovar o spec de design 📅 2026-08-15 #task
- [ ] Escrever o plano de implementação 📅 2026-08-16 #task

---
**See also:** [[Atendente IA]] | [[Guilherme Figueredo]]
