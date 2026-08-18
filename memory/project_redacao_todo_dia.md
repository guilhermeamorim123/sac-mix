---
name: project-redacao-todo-dia
description: Redação Todo Dia — infoproduto de correção de redação do ENEM 2026, estado em 17/08/2026 e o que trava
metadata:
  type: project
---

Infoproduto sazonal para o **ENEM 2026** (provas 8 e 15/11): o aluno fotografa
a redação manuscrita e recebe correção nas 5 competências. Dois planos —
**R$45,90** (corretor) e **R$59,90** (com ebook de redação + exercícios).
App será Next.js na Vercel.

**Estado em 17/08/2026:** o harness de calibração está construído e testado
(93 testes, branch `feat/redacao-todo-dia-corretor`), mas **nada rodou contra
a API** — falta a `ANTHROPIC_API_KEY` e o conjunto de 20 redações com nota
conhecida.

**Os dois números que decidem o projeto**, e que saem da mesma rodada:
- erro médio da correção ≤ 80 pontos no total e ≤ 40 por competência
- custo por correção — no `effort` alto ele fica em ~R$1,20, o que faz o plano
  de R$45,90 **dar prejuízo** em quem usa. A varredura de `effort` é
  pré-condição do preço, não otimização

**Why:** o dono tem cinco produtos técnicos prontos e receita zero — o gargalo
nunca foi construir. A semana 1 foi desenhada como porta de saída justamente
para o projeto poder morrer barato.

**How to apply:** quando este projeto voltar, perguntar **se a calibração
rodou**, não o que foi construído. O plano da semana 2 (app + ebook) foi
deliberadamente adiado até haver dado. E lembrar que o [[project-atendente-ia]]
vence em **13/09** e está parado — os dois não cabem no mesmo mês.

Ver `projects/redacao-todo-dia/`.
