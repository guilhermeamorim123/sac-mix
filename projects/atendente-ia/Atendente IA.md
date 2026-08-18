---
type: project
name: "Atendente IA"
status: "em andamento"
owner: "[[Guilherme Figueredo]]"
started: 2026-08-14
tags:
  - project/atendente-ia
  - project/active
---

# Atendente IA

## Description

Operação de venda de automação de atendimento para comércio local, com meta de
**R$ 1.000 a R$ 3.000 de receita em 30 dias** (até 13/09/2026).

Nasceu de uma constatação: o vault tem cinco produtos técnicos construídos
([[project-livewire|Livewire]], CLIENTIA, DragX, BUSCAPP, fábrica de agentes) e
**receita zero**. O gargalo nunca foi capacidade de construir — é distribuição.
Este projeto não constrói um sexto produto: vende o que já se sabe fazer, à mão,
cobrando antes de entregar.

Restrições que definem o desenho:
- **Sem canal de distribuição** — toda aquisição é prospecção fria
- **30 dias** — prazo curto elimina venda consultiva e escopo aberto
- **Tempo limitado** — Guilherme está no último ano do ensino médio

## A oferta (produto único, não "sob medida")

A decisão mais importante do projeto: **vender o mesmo produto repetido**, com
preço de tabela e demo pronta. "Sob medida" de verdade significa orçamento
demorado, entrega imprevisível e cliente indeciso — inviável em 30 dias.
Customiza-se os 20% de cima (perguntas, tom, catálogo), nunca os 100%.

**Produto:** atendente de IA no WhatsApp que responde em segundos, 24h por dia.

| Item | Definição |
|---|---|
| **Faz** | Responde as ~20 perguntas que somam 80% do volume (preço, horário, endereço, formas de pagamento, o que é o procedimento X); qualifica intenção; agenda ou passa pro humano com contexto; painel de conversas e leads |
| **Preço** | **R$ 1.200 de setup + R$ 297/mês** a partir do 2º mês |
| **Prazo** | 5 dias úteis após o pagamento |
| **Pagamento** | 50% na assinatura + 50% na entrega, ou 100% antecipado |
| **Garantia** | 15 dias — não gostou, devolve o setup |
| **NÃO inclui** | Integração com sistema de gestão, e-commerce, cobrança online, mudança de escopo após o aceite |

Racional do preço: o setup sozinho bate a meta com 2 vendas (R$ 2.400). A
mensalidade é o ativo que sobra depois. R$ 297 fica abaixo do limiar de "preciso
falar com meu sócio" e acima do de "barato demais pra prestar".

A cláusula **NÃO inclui**, escrita na proposta, é o que impede o projeto de virar
consultoria não remunerada.

## O nicho

**Recomendado: estética e beleza de alto ticket** — clínicas de estética,
studios de sobrancelha/cílios, depilação a laser, micropigmentação.

Por quê:
- Cada lead perdido vale R$ 300 a R$ 3.000 em procedimento — a conta da dor se
  faz na frente do dono, com o número dele
- Decisor acessível: dono ou gerente, não comitê
- WhatsApp e Instagram públicos no Google Maps → lista fácil de montar
- A mesma demo serve para 100 delas
- Pagam ticket alto sem estranhar

**Alternativa forte:** imobiliárias e corretores — velocidade de resposta
determina fechamento, e o lead deles é caro.

**Evitar nestes 30 dias:** restaurante (margem baixa), material de construção
(dono resistente a software), vendedor de ML/e-commerce (prospecção digital é
lenta sem canal), odontologia e clínicas médicas (dado de saúde é dado sensível
na LGPD — viável, mas exige uma camada a mais que atrasa a primeira venda).

### Como montar a lista sem canal

Google Maps é a mina: buscar `clínica de estética <cidade>` devolve telefone,
WhatsApp, Instagram e — o que importa — **número e nota de avaliações**.

Critério de priorização:
1. **Muitas avaliações** = volume de cliente = dor real
2. **Instagram ativo** = já gasta dinheiro para gerar lead que está perdendo
3. **Perto fisicamente** = candidato a abordagem presencial, que converte muito
   mais que a digital

Meta: **100 nomes até o dia 5**. Leva ~3h.

## A demo é o ativo que destrava tudo

Antes de qualquer abordagem, existe **uma** demo funcionando: uma clínica
fictícia, com um número de WhatsApp real que o prospect pode mandar mensagem e
ver respondendo na hora.

Isso é o que converte abordagem fria em conversa. *"Manda um oi nesse número e
vê"* vale mais que qualquer pitch — o produto se demonstra sozinho, em 10
segundos, no aparelho da pessoa.

Base técnica já existe: bridge do WhatsApp rodando em `whatsapp-mcp/` + Claude
API. Prazo: 3 dias.

## Funil e matemática (30 dias)

| Etapa | Número | Taxa |
|---|---|---|
| Lista | 100 | — |
| Contatados | 80 | — |
| Responderam | 20–30 | 25–40% |
| Demo agendada | 6–9 | ~30% |
| **Venda** | **2–3** | 25–35% |

2 × R$ 1.200 = **R$ 2.400** — meta batida.

**O número que não pode falhar é 80 abordagens.** São ~4 por dia útil, cerca de
40 minutos. O erro clássico é parar em 15 e concluir que "não funciona" — 15
abordagens não testam nada.

## Scripts de abordagem

Regras: nunca abrir com "Olá, tudo bem? Meu nome é..."; abrir com observação
específica daquela loja; uma pergunta só, fácil de responder; **sem link no
primeiro contato** (o WhatsApp pune).

**Primeiro contato:**

> Oi, [Nome]! Vi a [Clínica] no Google — [N] avaliações, nota [X]. Pergunta
> rápida: quando chega mensagem aqui fora do horário ou no fim de semana, alguém
> responde na hora ou fica pra depois?

**Depois de "fica pra depois" / "demora":**

> É o padrão, e é onde o agendamento se perde. Montei um atendente de IA que
> responde em segundos, 24h — tira dúvida de preço e procedimento e já agenda.
> Tenho um número de demonstração rodando: quer mandar um "oi" nele e ver como
> responde? Sem compromisso.

**Presencial** (converte muito mais — cerca de 70% viram conversa): chegar na
recepção, pedir o responsável, abrir a demo no celular ali mesmo. Reservar para
as mais próximas da lista.

## Cronograma

| Dias | O quê |
|---|---|
| 1–3 | Construir a demo (um nicho, uma demo) |
| 4–5 | Lista de 100 no Google Maps + proposta de 1 página |
| 6–20 | 4 a 6 abordagens por dia; demos conforme aparecem |
| 10–25 | Primeira venda esperada → entrega em 5 dias |
| 20–30 | Segunda venda → entrega |

**Regra inegociável: não construir nada para um cliente antes do pagamento do
setup.**

## Key Decisions

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-08-14 | Vender serviço, não SaaS | O plano do Livewire coloca cobrança na fase 4, depois de worker na nuvem, extensão e onboarding — meses, não semanas |
| 2 | 2026-08-14 | Produto único de tabela, não "sob medida" | Escopo aberto inviabiliza fechar em 30 dias |
| 3 | 2026-08-14 | R$ 1.200 setup + R$ 297/mês | 2 vendas de setup batem a meta; a mensalidade é o ativo residual |
| 4 | 2026-08-14 | Nicho de estética/beleza, não odonto | Mesma dor e mesmo ticket, sem a camada de dado sensível da LGPD |
| 5 | 2026-08-14 | Demo pública antes da primeira abordagem | Converte prospecção fria em conversa sem depender de pitch |

## Current Risks & Blockers

| # | Risk/Blocker | Severity | Status |
|---|-------------|----------|--------|
| 1 | **Construir em vez de vender** — o perfil é de builder; a tentação é polir a demo por 30 dias e fazer 0 abordagens | **Alta** | Open — mitigação: demo tem prazo fechado de 3 dias |
| 2 | **Bloqueio do WhatsApp** por mensagem fria em volume no número pessoal | Alta | Open — mitigação: chip separado, ritmo humano, nunca colar texto idêntico, presencial nas próximas |
| 3 | Tempo — último ano do ensino médio | Média | Open — 4 abordagens/dia = ~40 min, cabe; o que não cabe é reconstruir do zero por cliente |
| 4 | LGPD — o bot conversa com cliente final; declarar que o atendimento é automatizado e não guardar mais dado que o necessário | Média | Open — resolver na proposta, antes da 1ª entrega |
| 5 | Parar o funil cedo demais (15 abordagens em vez de 80) e concluir que não funciona | Média | Open |

## Notes

Ativos do vault reaproveitáveis aqui: bridge do WhatsApp (`whatsapp-mcp/`), a
fábrica de agentes ([[project-livewire]] mostrou o padrão de catálogo +
triagem + Claude), e o aprendizado de custo por mensagem do plano 002 — a
triagem determinística que cortou 71% das chamadas de IA vale igual aqui.

Se a meta for batida, a decisão seguinte é se isto vira operação recorrente ou
se o caixa financia a fase 0 do [[project-livewire|Livewire]].

## Tarefas

- [ ] Escolher a cidade/região alvo e travar o nicho 📅 2026-08-15 #task
- [ ] Construir a demo do atendente com número de WhatsApp real 📅 2026-08-17 #task
- [ ] Montar lista de 100 negócios no Google Maps 📅 2026-08-19 #task
- [ ] Escrever a proposta de 1 página (com o "NÃO inclui") 📅 2026-08-19 #task
- [ ] Comprar chip separado para prospecção 📅 2026-08-19 #task
- [ ] 80 abordagens (4–6/dia) 📅 2026-09-03 #task
- [ ] Primeira venda 📅 2026-09-05 #task
- [ ] Segunda venda 📅 2026-09-13 #task

---
**See also:** [[MOC Projects]] | [[Guilherme Figueredo]]
