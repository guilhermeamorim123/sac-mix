# Plano 002: Arquitetura do Livewire como SaaS multi-cliente

> **Escopo**: este é um documento de arquitetura, não um plano de execução
> passo a passo. Ele decide *o quê* e *por quê*; os planos de implementação
> (003+) saem daqui, um por fase.
>
> **Projeto**: Livewire (`tiktok-copilot/`), não o cortador CUTTER_E326 dos
> outros planos desta pasta.

## Status

- **Prioridade**: P1 para as fases 1 e 2; P2 daí em diante
- **Escrito em**: 06/08/2026, commit `44b76a0`
- **Estado atual do produto**: agente local + painel funcionando, um cliente
  (Mix Conecta), ainda não validado numa live real

## O problema

O Livewire de hoje funciona para uma loja: a sua. Ele não vira SaaS por três
motivos, em ordem de gravidade.

**1. Todo cliente recebe a chave mestra.** O `.env` do agente guarda a
`service_role` do Supabase, que passa por cima do RLS. Entregar isso ao segundo
cliente é entregar junto os leads, os WhatsApps e o histórico de todos os
outros. Não é risco teórico: é um arquivo de texto no PC de um desconhecido.

**2. A instalação é impossível para um lojista.** Python, venv, pip,
`playwright install chromium`, Chrome aberto com porta de debug, `.env`
preenchido à mão. Isso não é onboarding, é suporte técnico individual — a
R$ 60/mês, o primeiro atendimento já come o ano inteiro de assinatura.

**3. Quem transmite pelo celular está fora.** E é a maioria dos vendedores
pequenos, justamente o público-alvo.

## O corte que resolve

O agente faz duas coisas com exigências completamente diferentes:

| Metade | Precisa de | Pode rodar na nuvem? |
|---|---|---|
| **Ler o chat** — TikTokLive → Claude → banco | só o `@` da live | **Sim** |
| **Digitar no chat** — Playwright no LIVE Center | sessão logada do TikTok num navegador | **Não** |

As duas só estão juntas porque nasceram no mesmo arquivo. Separá-las resolve os
três problemas de uma vez:

- a leitura sobe para a nuvem → **zero instalação**, funciona em qualquer
  aparelho com navegador, inclusive celular;
- a `service_role` fica na *nossa* infraestrutura e nunca é entregue a ninguém;
- só quem quiser auto-envio instala algo — e o que ele instala deixa de ser
  Python.

Vale ter clareza sobre a proporção: a leitura é onde está quase todo o valor do
produto. Sugestão de resposta, lead quente, captura de WhatsApp, coaching, nota
da live — tudo isso é leitura. O auto-envio é conveniência, não o produto.

## Arquitetura alvo

```
    NOSSA INFRA                    BANCO                   CLIENTE
┌────────────────────┐      ┌──────────────────┐    ┌──────────────────┐
│ Orquestrador       │      │   Supabase       │    │ Painel (web)     │
│   claim de sessoes │      │                  │    │  PC, tablet ou   │
│        ↓           │      │  live_sessions   │<──>│  celular         │
│ Worker de live     │─────>│  messages        │    │  [Iniciar]       │
│   TikTokLive       │      │  leads           │    │  [Copiar]        │
│   Claude           │      │  lives           │    │  [Enviar] ──┐    │
│   service_role     │<─────│  produtos/config │    └─────────────┼────┘
└────────────────────┘      │  commands        │<─────────────────┘
                            └──────────────────┘           │
                                     │  realtime           │
                                     v                     │
                            ┌──────────────────┐           │
                            │ Extensao Chrome  │<──────────┘
                            │  (so no desktop) │
                            │  digita no LIVE  │
                            │  Center, logada  │
                            │  como o vendedor │
                            └──────────────────┘
```

Três planos, três donos:

### 1. Worker de live (nossa infra)

Um processo que segura N lives simultâneas como tasks asyncio — não um
container por live. O websocket é barato; o que custa é o Claude. Container por
live só se justificaria por isolamento, e o isolamento que importa (dados) já
está no RLS.

Ciclo de vida: o vendedor aperta **Iniciar copiloto** no painel → o painel
insere uma linha em `live_sessions` com status `solicitada` → o orquestrador
reivindica a sessão, sobe a task, e passa a bater heartbeat. Encerra quando o
TikTokLive desconecta e não volta dentro de uma janela de tolerância, ou quando
o vendedor encerra no painel.

O que ele mantém do agente atual: `ingest`, `ai`, `catalog`, `store` (lado
Supabase), a avaliação da live. O que ele perde: `sender` e todo o polling de
`commands`.

### 2. Extensão de Chrome (máquina do cliente, opcional)

Substitui o Playwright inteiro. Ela já vive dentro do navegador onde o vendedor
está logado — some de uma vez com Python, com a porta de debug do Chrome e com
o `.env` na máquina dele. Instalação vira um clique.

Responsabilidades: escutar `commands` da própria loja via Realtime
(autenticada como o usuário do vendedor, com RLS valendo), digitar na caixa de
comentário do LIVE Center com a mesma cadência humana do `sender.py` atual, e
marcar o comando como `done`/`failed`.

As três travas continuam: kill switch, throttle e filtro de intenção. A
diferença é que agora o filtro é decidido no servidor (o worker só enfileira
comando para o que passou) e a extensão ainda reforça o throttle do seu lado —
duas barreiras em vez de uma.

**Problema conhecido, e não é técnico**: a Chrome Web Store provavelmente
rejeita uma extensão que automatiza o TikTok contra os Termos. Distribuição
vira modo desenvolvedor ou CRX auto-hospedado, o que reintroduz fricção de
suporte — menor que a do Python, mas real. Decidir isso antes de construir.

### 3. Painel (já existe, ganha três coisas)

- botão **Iniciar / Encerrar copiloto**, que é o que cria a `live_session`;
- indicador de saúde: worker conectado? extensão conectada? sem isso o vendedor
  não sabe se o silêncio é chat parado ou sistema caído;
- no mobile, **Copiar** vira a ação primária, com alvo grande — o Enviar fica
  desabilitado e explicado quando não há extensão.

## Autenticação e isolamento

É a fase que destrava o segundo cliente, e ela é pequena.

Regra única: **a `service_role` nunca sai da nossa infraestrutura.**

- **Worker**: usa `service_role`. Correto — é backend nosso, mesmo limite de
  confiança de qualquer SaaS.
- **Extensão**: autentica como o usuário do vendedor (a mesma conta do painel),
  com a chave publicável + JWT. O RLS já existe e já funciona — `tem_acesso()` e
  as policies `acesso_loja` estão no `schema.sql`.
- **Agente local**, para quem continuar usando: login por email/senha ou token
  por loja, nunca `service_role`. Na prática é trocar o `create_client(url,
  service_key)` do `store.py` por um `sign_in_with_password` e deixar o RLS
  trabalhar.

Junto com isso, derrubar os `default 'mix-conecta'` de `seller_id` em
`messages`, `leads`, `commands`, `lives` e `replay_supervisao` (comando pronto
no rodapé do `schema.sql`). Com default, um insert que esqueça o `seller_id`
cai silenciosamente na loja errada — e "silenciosamente" é a palavra ruim aí.

## O que muda no banco

| Mudança | Por quê |
|---|---|
| nova tabela `live_sessions` | o painel precisa pedir uma live e ver se ela está de pé |
| `commands` ganha `origem` (`painel`/`worker`) | saber quem pediu, para auditoria |
| derrubar defaults de `seller_id` | ver acima |
| `sellers` ganha `status_extensao`/`ultimo_heartbeat` | o painel mostra se a ponta de envio existe |

Nada disso quebra o painel atual — são adições.

## Fases

Cada fase entrega algo utilizável sozinha. A ordem é por destravamento, não por
tamanho.

| # | Fase | Destrava | Esforço |
|---|---|---|---|
| 0 | Validar na Mix Conecta com o agente local, como está hoje | saber se o produto presta antes de reescrevê-lo | — |
| 1 | Tirar a `service_role` do cliente + derrubar defaults | **o segundo cliente** | P |
| 2 | Worker de leitura na nuvem + `live_sessions` + Iniciar/Encerrar | zero instalação; **celular** | M |
| 3 | Extensão de Chrome substitui o Playwright | auto-envio sem Python | M |
| 4 | Onboarding self-service (criar loja, vincular usuário, planos) + cobrança | vender sem você no meio | M |

A fase 2 depende de uma verificação que ainda não foi feita — ver riscos.

## Economia unitária e preço

Conta feita em 06/08/2026 com os parâmetros reais do agente (lote de 12,
system prompt medido em 917 tokens, catálogo da Mix Conecta). Preços da API:
Opus 5 US$ 5/US$ 25 por milhão de tokens (entrada/saída), Haiku 4.5 US$ 1/US$ 5.
Dólar a R$ 5,50.

### Custo por hora de live

| Cenário | msgs/h | Opus 5 | Haiku 4.5 | Haiku + triagem |
|---|---|---|---|---|
| Tranquila | 300 | $ 1,06 | $ 0,18 | $ 0,06 |
| Movimentada | 900 | $ 3,19 | $ 0,54 | $ 0,19 |
| Viral | 2.000 | $ 7,08 | $ 1,20 | $ 0,42 |

A saída domina o custo (~95%). Por isso o modelo pesa mais que qualquer outra
variável, e reduzir o **número de mensagens classificadas** é a segunda alavanca.

### As duas decisões que fazem o preço fechar

**1. Haiku 4.5 como motor, não Opus 5.** Classificar uma pergunta de chat e
escrever 200 caracteres com o catálogo à frente não é tarefa de modelo grande.
Um vendedor de 3 lives/dia custaria R$ 552/mês em Opus contra R$ 94 em Haiku —
com a triagem já aplicada nos dois. Sonnet 5 fica no meio (R$ 296) como plano B
se a qualidade do Haiku não segurar; a decisão sai de rodar a mesma live nos
dois e comparar onde discordam, não de impressão.

**2. Triagem determinística antes da IA.** Implementada em `triagem.py`
(06/08/2026): emoji, saudação e reação não vão para a API. A mensagem continua
sendo gravada e aparecendo no painel — só não vira token. Num lote realista de
teste, 71% do chat foi filtrado. **Não é otimização: sem ela o Studio custa
R$ 268/mês em IA e a margem cai de 63% para 30%.**

Regra de projeto da triagem: o erro caro é o falso positivo (filtrar quem ia
comprar). Qualquer sinal de interesse — interrogação, número, palavra
comercial, nome de produto — manda para a IA antes de qualquer teste de
trivialidade.

### Estrutura de preço

O custo **não escala por vendedor, escala por hora de live**. Preço único cobra
o mesmo de quem faz 3 lives por semana e de quem faz 3 por dia — o leve
subsidia o pesado, e o pesado é o melhor cliente. Daí as faixas por hora:

| Plano | Limite | Preço | Custo real (pior caso) | Margem bruta |
|---|---|---|---|---|
| Essencial | 10 h/mês | R$ 60 | ~R$ 20 | 67% |
| Solo | 20 h/mês | R$ 97 | ~R$ 31 | 68% |
| Pro | 60 h/mês | R$ 197 | ~R$ 78 | 61% |
| Studio | 120 h/mês | R$ 397 | ~R$ 148 | 63% |

O R$ 60 original não estava errado — estava precificado para um vendedor de 2 a
3 lives por semana. Aplicado a um de 3 por dia, dava prejuízo de 6x.

Medir hora de live é grátis: `lives.duracao_min` já é gravado. Falta o painel
somar o mês e mostrar o consumo. No estouro, o menos hostil é continuar
sugerindo e desligar o auto-envio, com aviso.

### Ressalvas

- A margem é **bruta de IA e infra**. Não inclui Pix/Stripe (~4%), suporte, nem
  aquisição.
- A infra (R$ 8 a R$ 22 por cliente) é estimativa, não medida — só sai de
  verdade na fase 2.
- **Exposição cambial:** o custo é em dólar, a receita em real. A R$ 7,00 o
  dólar, a margem do Studio cai de 63% para ~54%. A folga que a triagem criou é
  o que absorve isso. Revisar preço quando o câmbio andar mais de 15%.
- A taxa de 71% saiu de um lote de teste, não de uma live. O agente loga
  `triagem: X%` no encerramento de cada live — esse é o número que valida ou
  derruba a tabela inteira.

## Riscos a verificar antes de escalar

**Sign server do TikTokLive.** A biblioteca depende de um serviço de assinatura
para abrir o websocket, com limite por IP e por chave. Uma live não sente.
Cinquenta lives simultâneas saindo do mesmo datacenter, sente. Antes de
dimensionar a fase 2: subir um container, conectar numa live real de um IP de
nuvem e ver o que acontece; e ler a documentação atual sobre limites e plano
pago. Se o bloqueio for duro, a alternativa é manter a leitura local para quem
tem PC e oferecer nuvem só no plano de cima — o que muda bastante o desenho.

**Distribuição da extensão.** Decidir antes de construir (ver acima).

**LGPD.** O produto captura número de celular de gente que comentou numa live
pública e monta um CRM com isso. Com uma loja, é o seu problema. Com 3.000, é
um banco de dados de dado pessoal de terceiros operado por você, com base legal
a definir, política de retenção, e um caminho de exclusão a pedido. Isso não
bloqueia a fase 1 nem a 2, mas precisa estar resolvido antes da 4 — cobrar por
um serviço torna a responsabilidade bem menos ambígua.

**Termos do TikTok.** Continua valendo o que o README já diz. A extensão não
muda a natureza do auto-envio, só o mecanismo. O que muda com o SaaS é a
escala: o risco deixa de ser "minha conta pode cair" e passa a ser "posso
derrubar a conta de 3.000 clientes pagantes". Vale considerar se o auto-envio
deve mesmo ser vendido, ou ficar como recurso que o cliente liga por conta e
risco, com aceite explícito.

## O que não fazer

**Não guardar cookie de sessão do TikTok no servidor** para enviar mensagem de
lá. Tecnicamente é o caminho mais curto para auto-envio sem instalar nada — e é
o pior negócio do documento: vira custódia de credencial de 3.000 contas, com
tudo que isso implica se vazar, e uma sessão que quebra sozinha a cada
reautenticação. A extensão faz a mesma coisa com o risco no lugar certo: na
máquina de quem escolheu correr o risco.
