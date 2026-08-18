---
type: project
name: "Redação Todo Dia"
status: "em andamento"
owner: "[[Guilherme Figueredo]]"
started: 2026-08-17
tags:
  - project/redacao-todo-dia
  - project/active
---

# Redação Todo Dia

## Description

Infoproduto sazonal para o **ENEM 2026** (provas em 8 e 15 de novembro),
vendido com tráfego pago no Meta para público aberto. O aluno escreve uma
redação à mão, fotografa, e recebe correção nas 5 competências do ENEM em
minutos.

O diferencial não é o conteúdo — é o **retorno**. Quase todo produto de ENEM
vende bem e é abandonado em duas semanas porque o valor está num PDF que não
cobra nada de volta. Aqui cada correção é a dose que faz o aluno voltar, e o
gráfico da nota subindo é o que faz continuar.

Design completo em [[2026-08-17-redacao-todo-dia-design]].
Plano da semana 1 em [[003-redacao-todo-dia-corretor]].

## Estado em 17/08/2026

| Peça | Estado |
|---|---|
| Harness de calibração (CLI Python) | **Construído**, 93 testes passando, branch `feat/redacao-todo-dia-corretor` |
| Calibração contra nota conhecida | **Bloqueada** — falta a chave da API e o conjunto de 20 redações |
| Varredura de `effort` (custo) | Bloqueada pela mesma chave |
| App (Next.js na Vercel) | Não começou — só existe se a calibração passar |
| Ebook com exercícios | Não começou |
| Landing e checkout | Não começou |

## Key Decisions

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-08-17 | Tráfego pago, público aberto | Escolha do dono; é a habilidade central dele. Descartada a venda para os colegas do IPÊ, que teria distribuição quente mas teto de ~100 pessoas |
| 2 | 2026-08-17 | Redação, não plano de estudos nem revisão de conteúdo | É a única dor do ENEM onde "comprar" e "usar" podem ser a mesma coisa |
| 3 | 2026-08-17 | Transcrição confirmada pelo aluno antes da avaliação | Converte o maior risco técnico (OCR de letra ruim) numa tela de conferência em vez de numa correção errada |
| 4 | 2026-08-17 | Promessa de método, nunca de resultado | Passa na política de Unrealistic Outcomes do Meta; lição já aprendida no [[Infoproduto DE]] |
| 5 | 2026-08-17 | Toda regra determinística do ENEM fica no código, não no modelo | Somar cinco números e aplicar zeramento é onde LLM erra sem ganhar nada em troca |
| 6 | 2026-08-17 | Não usar a bridge WhatsApp de `whatsapp-mcp/` | Cliente não-oficial; com clientes pagantes o número é banido |
| 7 | 2026-08-17 | Dois planos: R$45,90 (corretor) e R$59,90 (completo, com ebook) | Degrau em conteúdo e não em cota: PDF tem custo marginal zero, então os R$14 entram quase inteiros. Separar por "mais correções" daria margem pior ao plano caro |
| 8 | 2026-08-17 | App em Next.js na Vercel, não no Lovable | Escolha do dono |
| 9 | 2026-08-17 | Semana 1 é porta de saída explícita | Se a correção não for confiável, o projeto morre gastando uma semana em vez de uma semana mais app, landing e ebook |

## Current Risks & Blockers

| # | Risk/Blocker | Severity | Status |
|---|-------------|----------|--------|
| 1 | **Conjunto de 20 redações com nota conhecida** — depende de terceiros (cursinho, professor, simulado). O INEP só publica as nota 1000 | **Alta** | Open — é o item que pode atrasar a semana |
| 2 | `ANTHROPIC_API_KEY` não existe na máquina | Alta | Open — o dono foi buscar em 17/08 |
| 3 | **Custo de IA come ~70% da receita** no plano de R$45,90. A varendura de `effort` virou pré-condição do preço, não otimização | **Alta** | Open — mede junto com a calibração |
| 4 | Qualidade da correção pode sair inconsistente | Alta | Open — é o que a calibração mede |
| 5 | OCR de letra manuscrita de adolescente | Alta | Open — testável hoje com 3 redações, sem depender do conjunto de 20 |
| 6 | **Competir por tempo com o [[Atendente IA]]**, que vence em 13/09 e está parado | **Alta** | Open — os dois não cabem no mesmo mês |
| 7 | Janela de venda fecha em meados de outubro | Média | Open |

## Notes

Três erros meus (Claude) foram pegos por revisão adversarial em 17/08 e valem
memória: as regras de anulação do ENEM estavam erradas em três pontos (só a
cartilha do INEP resolveu), o modelo avaliador estava inventando a contagem de
linhas que dispara a anulação, e a estimativa de custo estava 3× baixa por não
contar o thinking do Opus 5. Nenhum dos três aparecia nos testes.

Próximo passo assim que a chave chegar: rodar `corrigir` com 3 redações
manuscritas reais, incluindo letra ruim. Custa ~R$4 e testa os dois maiores
riscos sem depender do conjunto de 20.

---
**See also:** [[Atendente IA]] | [[Infoproduto DE]] | [[Guilherme Figueredo]]
