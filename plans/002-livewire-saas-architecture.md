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

## Economia unitária: um alerta

A R$ 60/mês (≈ US$ 11) por vendedor, com `claude-opus-5` e uma live de uma hora
custando "poucos dólares", **a conta não fecha**. Um vendedor que faça 20 lives
por mês consome muito mais do que paga. O produto fica com margem negativa
exatamente nos clientes mais engajados, que é o pior formato possível.

Dois movimentos resolvem, e eles se somam:

1. **Filtrar antes de gastar token.** A maior parte do chat de live é emoji,
   "oi", "boa noite" e spam — coisa de `lead_score` 0 a 2. Isso não precisa de
   modelo nenhum: um filtro determinístico (comprimento, ausência de verbo ou
   de interrogação, lista de saudações, mensagem repetida) descarta a maioria
   antes da chamada. Estimativa a medir na primeira live real, mas cortar 60-70%
   das mensagens é plausível.
2. **Haiku como padrão, Opus como exceção.** Classificar e redigir 200
   caracteres é tarefa em que o Haiku vai bem. O `.env` já permite a troca;
   falta medir os dois lado a lado numa live de verdade e decidir com número, não
   com impressão.

Medir isso na fase 0 é mais importante que qualquer código da fase 2 — é o que
diz se o preço de R$ 60 se sustenta ou precisa mudar.

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
