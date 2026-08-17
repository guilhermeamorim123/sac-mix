---
type: project
name: "Freela Gringa"
status: "em andamento"
owner: "[[Guilherme Figueredo]]"
started: 2026-08-17
tags:
  - project/freela-gringa
  - project/active
---

# Freela Gringa — chatbot de WhatsApp com IA, vendido em dólar

## Por que este caminho

Todas as outras tentativas exigiam **criar demanda do zero**: convencer alemão a
comprar e-book de horta, convencer dono de clínica a querer automação. Aqui a
demanda já existe e é medida — no Upwork, "desenvolvimento de chatbot com IA"
cresceu 71% ano a ano, e no Fiverr a busca por "AI automation" subiu 136% em
seis meses.

**A plataforma é a distribuição.** É a única coisa que resolve o gargalo que
aparece em todos os projetos deste vault.

E o produto já está meio pronto: o [[Atendente IA]] é exatamente essa oferta,
com a diferença de que aqui alguém já está procurando por ela, e paga em dólar.

## A correção técnica que evita queimar cliente

O `whatsapp-mcp` do vault conecta via WhatsApp Web não oficial. **Serve para
demo e uso próprio. Não serve para cliente pagante.**

Usar bridge não oficial no número de um cliente viola os termos do WhatsApp e
pode derrubar o número dele — que muitas vezes é o número principal do negócio.
Isso não é risco teórico: é o jeito mais rápido de transformar um cliente
satisfeito em um pedido de reembolso e uma avaliação de uma estrela.

**Para trabalho pago, use a WhatsApp Business Cloud API oficial**, da própria
Meta. Tem camada gratuita e depois cobra por conversa. O cliente faz a
verificação do Business Manager dele; você faz a integração.

## Plataforma

Começar pelo **Fiverr**, migrar para o **Upwork** depois das primeiras
avaliações.

| | Fiverr | Upwork |
|---|---|---|
| Como chega cliente | Ele acha seu anúncio | Você envia proposta |
| Precisa falar inglês ao vivo | Raramente | Frequente |
| Taxa | 20% | 10%, e **0%** em especialidade de alta demanda (dev de IA entra) |
| Bom para | Começar sem histórico | Projeto maior, depois de ter prova |

Fiverr primeiro porque o anúncio vende sozinho, de forma assíncrona — dá tempo
de escrever cada resposta com calma. Upwork exige proposta e frequentemente
chamada de vídeo.

## Preço

Os três primeiros trabalhos são **compra de avaliação**, não lucro.

| Fase | Basic | Standard | Premium |
|---|---|---|---|
| Primeiras 3 vendas | US$ 75 | US$ 180 | US$ 340 |
| Depois de 3 avaliações 5★ | US$ 145 | US$ 320 | US$ 590 |
| Depois de 10 avaliações | US$ 245 | US$ 480 | US$ 890 |

Mesmo o preço de largada resolve o problema: **US$ 340 ≈ R$ 1.800.** Dois
Premium batem a meta original de 30 dias.

## Recebimento

Payoneer ou Wise. **Cuidado com o câmbio:** freelancer brasileiro perde de 8% a
15% em conversão e transferência quando faz errado — em R$ 60 mil por ano isso
é de R$ 4.800 a R$ 9.000. Wise costuma sair melhor que banco.

## Gargalo real: a primeira avaliação

Sem histórico você compete com quem tem 200 avaliações. O que funciona:

1. **Preço de entrada baixo** nos três primeiros, assumido como custo de aquisição
2. **Resposta em minutos** — o Fiverr rankeia por tempo de resposta
3. **Nicho fechado** — "chatbot de WhatsApp" vende mais que "automação com IA",
   porque o comprador busca o específico
4. **Vídeo no anúncio** mostrando o bot respondendo de verdade. A maioria dos
   concorrentes só põe imagem estática
5. **A demo do plano do [[Atendente IA]]** serve aqui inteira — é o mesmo ativo

## Riscos

| # | Risco | Severidade | Mitigação |
|---|---|---|---|
| 1 | **Idade** — Fiverr e Upwork exigem 18 anos | **Alta** | Se for menor, a conta fica no CNPJ/nome de um maior da família |
| 2 | Inglês falado, se o cliente pedir chamada | Média | Fiverr é assíncrono; recusar chamada nos primeiros trabalhos é normal |
| 3 | Usar bridge não oficial e derrubar o número do cliente | **Alta** | Cloud API oficial em todo trabalho pago, sem exceção |
| 4 | Prometer prazo e não entregar com a escola | Média | Prazo de entrega com folga: 5 dias no Basic, não 2 |
| 5 | Primeiro trabalho não vir nunca | Média | Se em 3 semanas não vier pedido, revisar anúncio e preço antes de desistir |

## Ideia parada de propósito: multicanal

Guilherme levantou em 17/08 a ideia de o mesmo agente atender **todos os
canais**, puxando as APIs dos marketplaces além do WhatsApp — e ele mesmo
decidiu parar no WhatsApp por enquanto. A decisão está certa e fica registrada
como tal.

**Por que a ideia é mais real do que parece:** ele já fez isso. O
[[project-clientia|CLIENTIA]] é app de pós e pré-venda de Mercado Livre com
IA e auto-resposta, e o SAC Outops mexeu em endpoint do ML. Integração de
marketplace não é território novo.

**Por que vale como v2, não como v1:**

- Ticket muito maior. Atendimento multicanal é serviço de US$ 1.500 a 3.000,
  não de US$ 340
- Mais grudento. Quem centraliza atendimento não troca de fornecedor
- Na Europa os canais são outros: Amazon, eBay, Etsy, **Allegro** (Polônia),
  **Bol.com** (Holanda), **Cdiscount** (França), Zalando

**Por que não agora:** exige entender a API de cada marketplace, cada uma com
sua aprovação e seu limite. É semanas de trabalho antes da primeira venda —
o mesmo erro que já custou o dia de hoje. Um canal, uma venda, uma avaliação.
Depois o segundo canal, cobrando mais.

O gatilho para retomar: **depois da terceira venda no Fiverr.** Aí existe
avaliação, existe caixa, e existe prova de que alguém paga.

## Próximos passos

- [ ] Confirmar idade e definir em nome de quem fica a conta 📅 2026-08-18 #task
- [ ] Criar conta no Fiverr e completar perfil 📅 2026-08-18 #task
- [ ] Publicar o gig com a copy de `gig-fiverr.md` 📅 2026-08-19 #task
- [ ] Gravar vídeo de 45s do bot respondendo, para o anúncio 📅 2026-08-19 #task
- [ ] Montar bot de demonstração na Cloud API oficial 📅 2026-08-21 #task
- [ ] Primeira venda 📅 2026-09-05 #task

---
**See also:** [[Atendente IA]] | [[Guilherme Figueredo]]
