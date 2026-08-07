# TikTok AI Co-pilot

Copiloto de IA para vendedores de live commerce no TikTok. Lê o chat da live em
tempo real, classifica cada mensagem, sugere (ou envia) respostas, captura
WhatsApp e pontua leads.

Primeiro uso: Mix Conecta, para validar. Depois: SaaS a R$ 60/mês por vendedor.

## Como as peças se encaixam

```
PC do vendedor                    Nuvem                    Navegador
┌──────────────────┐         ┌──────────────┐        ┌──────────────┐
│ agent.py         │         │  Supabase    │        │ Painel       │
│                  │  write  │              │realtime│ (Lovable)    │
│ TikTokLive ──────┼────────>│  messages    ├───────>│ Ao Vivo      │
│      ↓           │         │  leads       │        │ Lives Prontas│
│ Claude           │         │  lives       │        │              │
│      ↓           │  poll   │  commands    │  write │ [Enviar]     │
│ Playwright ──────┼<────────┤              │<───────┤ [Reexibir]   │
│                  │         │              │        │              │
│ catálogo    ─────┼<────────┤  produtos    │<───────┤ Configurações│
│ configurações    │  poll   │  frete_regras│  write │ [Importar    │
│                  │         │  configuracoes        │  planilha]   │
└──────────────────┘         └──────────────┘        └──────────────┘
```

O agente roda **na máquina do vendedor** porque precisa de duas coisas que
navegador não faz: websocket do TikTok Live e controle do Chrome. O painel é web
e conversa com ele através do Supabase.

A conversa vai nos dois sentidos: o agente escreve o que acontece na live, e lê
de volta o catálogo e as preferências que o lojista mantém pelo painel.

| Arquivo | Função |
|---|---|
| `agent.py` | Orquestrador. É o que você executa. |
| `ingest.py` | Lê o chat da live (biblioteca TikTokLive) |
| `ai.py` | Classifica em lote e redige as respostas (Claude) |
| `store.py` | Persistência — SQLite local ou Supabase |
| `sender.py` | Digita no chat via Playwright (ver aviso abaixo) |
| `catalog.py` | Catálogo, frete e base de conhecimento (do banco ou do `products.json`) |
| `triagem.py` | Separa o chat que precisa de IA do que não precisa (ver abaixo) |
| `config.py` | `.env` (máquina) + tabela `configuracoes` (loja) |
| `custo.py` | Soma o que a API cobrou de verdade na live |
| `schema.sql` | Espelho do banco. Regerado a partir dele. |
| `LOVABLE_PROMPT.md` | Prompt que gerou o painel |
| `test_smoke.py` | Testes da lógica pura, sem rede |

---

## Instalação

```bash
cd tiktok-copilot
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium

copy .env.example .env          # e preencha
```

No `.env`, o mínimo para rodar é `ANTHROPIC_API_KEY` e `TIKTOK_USERNAME`.
Deixe `STORE_BACKEND=sqlite` e `AUTO_REPLY_ENABLED=false` no primeiro teste.

## De onde vem o catálogo

O que a IA sabe sobre a loja — produtos, preços, estoque, frete, políticas de
troca — é o que impede ela de inventar. **Preço errado aqui vira preço errado
dito no ar.** Por isso o agente tem duas origens, nunca as duas ao mesmo tempo:

| `STORE_BACKEND` | Catálogo e frete | Auto-resposta, teto/min, intents, tom de voz |
|---|---|---|
| `sqlite` | `products.json` | `.env` |
| `supabase` | tabelas `produtos`, `frete_regras`, `base_conhecimento` | tabela `configuracoes` |

No modo `supabase`, quem edita é o lojista, pelas Configurações do painel
(inclusive importando planilha do Seller Center). O `.env` vira só fallback.

Duas garantias que valem conhecer:

- **Catálogo vazio não sobe.** Se o banco responder sem nenhum produto ativo, o
  agente aborta com a mensagem dizendo onde cadastrar, em vez de entrar na live
  respondendo "não sei" para tudo.
- **Mudança no meio da live chega sozinha.** A cada `REFRESH_SECONDS` (padrão
  30) o agente relê catálogo e configurações. Corrigiu um preço às 20h15? A
  próxima mensagem já é respondida com ele. O prompt só é reconstruído quando
  algo de fato mudou, para não jogar fora o cache da Claude à toa.

Uma sutileza do interruptor de auto-resposta: o agente só obedece à tabela
`configuracoes` quando o valor **muda** lá. Assim um **PARAR TUDO** dado no
painel não é desfeito pelo refresh seguinte — ele vale até alguém religar a
chave nas Configurações.

E há um limite que o painel não vence: mesmo que alguém marque `reclamacao` na
lista de intents automáticos, o agente descarta. Reclamação, negociação e
qualquer coisa marcada como `requires_human` vão para o vendedor. Sempre.

## Triagem: o que não custa token

A maior parte do chat de uma live é emoji, "oi" e "top demais". Isso não precisa
de modelo nenhum para ser classificado — e mandar para a API custa o mesmo que
uma pergunta de verdade. O `triagem.py` separa os dois antes da chamada.

**Não é descarte, é triagem.** A mensagem continua sendo gravada e continua
aparecendo no chat do painel; ela só não vira token e não ganha sugestão de
resposta, porque não havia o que responder.

A ordem das checagens é sempre a mesma, e ela existe para proteger contra o
único erro caro aqui — filtrar alguém que ia comprar:

1. **Primeiro, tudo que indica interesse** manda para a IA: interrogação,
   qualquer número (quem larga o WhatsApp no chat é lead quente), palavra
   comercial (preço, frete, tem, quero, pix, tamanho, garantia…) ou o nome de um
   produto do catálogo.
2. **Só o que sobra** pode ser considerado trivial: emoji puro, "kkkkk",
   mensagem de menos de 3 caracteres, ou até 4 palavras todas na lista de
   saudações e reações.

Na dúvida, vai para a IA. Uma saudação classificada à toa custa frações de
centavo; um "quanto custa?" filtrado custa a venda.

No encerramento da live o log mostra a taxa:

```
triagem                71.4% (250 de 350 nao custaram token)
```

**Anote esse número a cada live.** É ele que valida a conta de custo do
`plans/002-livewire-saas-architecture.md` — e é o que decide se o preço fecha.

> O painel deve esconder da fila de resposta as mensagens sem `suggested_reply`
> — são as filtradas. Sem isso elas aparecem no fim da fila como cards vazios.

## Rodando

Com a live já no ar:

```bash
python agent.py
```

O terminal vai mostrar cada mensagem classificada:

```
14:32:07  INFO  agent  HOT [como_comprar/9] Ana Paula: como faço pra comprar o fone?
14:32:07  INFO  agent       WhatsApp capturado: 5511987654321 (@anapaula)
14:32:09  INFO  agent      [elogio/1] Marcos: top demais
```

`Ctrl+C` encerra e grava as métricas da live. O resumo final traz os dois
números que decidem o produto:

```
--- Resumo da live ---
  comentarios            412
  leads_captados         28
  whatsapps              11
  triagem                68.4% (282 de 412 nao custaram token)
--- Custo da IA ---
  modelo                 claude-opus-5
  chamadas a API         34
  tokens entrada         9,180 (+31,178 lidos do cache)
  tokens saida           38,400
  CUSTO REAL             US$ 1.0175  (US$ 1.02/hora)
```

**Anote esses dois a cada live.** A tabela de preço do
`plans/002-livewire-saas-architecture.md` inteira é estimativa; o `CUSTO REAL`
e a `triagem` são o que confirmam ou derrubam ela. Se aparecer o aviso
`o cache do catalogo nao pegou nenhuma vez`, o prompt ficou abaixo do mínimo
cacheável do modelo — no Haiku 4.5 esse mínimo é 4.096 tokens, contra 512 no
Opus 5.

## Testes

```bash
python test_smoke.py
```

Cobre a captura de WhatsApp, a trava de auto-envio, o filtro de intents vindo
do painel, a montagem do catálogo (arquivo e banco) e o cálculo de avaliação da
live. Não precisa de API key nem de rede.

---

## Auto-envio no chat — leia antes de ligar

O TikTok **não tem API de envio de mensagem**. O `sender.py` automatiza a
interface web do LIVE Center com Playwright. Isso contraria os Termos de Uso e
pode levar a **banimento da conta**. Foi uma decisão consciente do dono do
projeto. Recomendação que continua valendo: **teste numa conta secundária
primeiro**, não na conta principal da loja.

Três travas, checadas antes de cada envio:

1. **Kill switch** — a chave de auto-resposta nas Configurações do painel (ou
   `AUTO_REPLY_ENABLED=false` no modo local), mais o botão PARAR TUDO.
2. **Throttle** — teto por minuto (padrão 4, editável no painel), com intervalos
   aleatórios e digitação caractere a caractere. Cadência robótica é o que
   denuncia bot.
3. **Filtro de intenção** — só envia sozinho `preco`, `frete`, `prazo` e
   `como_comprar`. O lojista pode restringir mais essa lista no painel, nunca
   ampliá-la para reclamação ou negociação — isso é travado no código. Qualquer
   coisa que a IA marcou como `requires_human` vai para o vendedor. Sempre.

### Freio de emergência automático

Uma quarta trava, que não depende de ninguém estar olhando. A cada 5 segundos o
agente varre a tela do LIVE Center atrás de sinal de problema, em português e
inglês. Ele vigia três coisas:

| Sinal | O que é |
|---|---|
| **Aviso na tela** | banner ou modal com "violação", "diretrizes da comunidade", "conta restrita", "comentário removido"… |
| **Falhas seguidas** | 3 envios que não completaram — ou o DOM mudou, ou tem algo barrando |
| **Mensagem sem eco** | 2 mensagens que saíram sem erro e não apareceram no chat — a assinatura de shadow-block |

Qualquer um dos três **corta o auto-envio na hora** e desliga a chave no banco,
para ela aparecer desligada no painel — é assim que você fica sabendo. A partir
daí nem o botão Enviar passa: aprovação humana vale para uma mensagem, não para
continuar automatizando depois de um aviso.

Duas escolhas de projeto que valem explicar:

- **A leitura não para.** Você continua vendo o chat, os leads e as sugestões.
  O que morre é o robô digitando — justamente o que você quer que morra quando
  o TikTok reclama.
- **A live não é encerrada.** Isso é decisão sua. Um falso positivo não pode
  custar uma transmissão inteira; o sistema grita e você decide.

Para rearmar, ligue a chave de auto-resposta de novo no painel. Ter que fazer
isso na mão é intencional: você vê que travou antes de religar.

> A varredura lê só caixas de aviso, toast e modal — nunca o chat. Sem esse
> cuidado, um espectador digitando "isso é violação" travaria seu envio.

### O agente nunca vê sua senha

Você loga na mão, ele se anexa à sessão. Abra o Chrome assim:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="C:\chrome-tiktok"
```

Faça login no TikTok nessa janela e abra <https://livecenter.tiktok.com/live_monitor>.
Só então rode o `agent.py` com `AUTO_REPLY_ENABLED=true`.

Se o Chrome não estiver aberto assim, o agente avisa no log, desliga o
auto-envio e **continua funcionando normalmente** só sugerindo no painel.

> O DOM do TikTok muda sem aviso. Se aparecer "Campo de comentário não
> encontrado" no log, atualize a lista `INPUT_SELECTORS` em `sender.py`.

---

## Painel (Lovable + Supabase)

O painel já existe: projeto **Co-Piloto TikTok** no Lovable
(`558553c9-7d94-4a6c-a282-fb8828387ac0`), com o banco provisionado pelo Lovable
Cloud e o `schema.sql` já aplicado. Para apontar o agente para ele:

1. No Lovable, abra as configurações do backend do projeto e copie a URL do
   Supabase e a chave de **serviço** (`service_role`, ou `sb_secret_...` no
   formato novo). A chave publicável não serve: o agente precisa passar por
   cima do RLS.
2. No `.env`, mude para `STORE_BACKEND=supabase`, preencha `SUPABASE_URL` e
   `SUPABASE_SERVICE_KEY`, e deixe `SELLER_ID=mix-conecta` (precisa bater com
   uma linha de `sellers`).
3. Cadastre os produtos reais pela aba Produtos das Configurações — à mão ou
   importando a planilha exportada do Seller Center.

Para montar isso do zero noutro lugar, rode o `schema.sql` inteiro no SQL Editor
de um projeto Supabase novo e siga o `LOVABLE_PROMPT.md`.

O painel tem três áreas:

- **Ao Vivo** — chat, fila de respostas, leads quentes, coaching.
- **Lives Prontas** — biblioteca das lives gravadas, com nota (boa / regular /
  ruim), vendas por hora e recomendação de reexibir ou não.
- **Configurações** — produtos (com importação de planilha), frete, base de
  conhecimento e as preferências que o agente relê durante a live.

### Reexibição de live gravada

A página "Lives Prontas" exige **check-in de supervisor** para liberar o botão
de reexibir. Com `REPLAY_MODE=true`, o agente também trava o auto-envio se
ninguém marcar presença a cada `SUPERVISOR_INTERVAL_MIN` minutos.

Dois pontos a considerar antes de reexibir gravação como se fosse ao vivo:
é violação dos Termos do TikTok, e há exposição ao Art. 37 do CDC (publicidade
enganosa) se o cliente compra acreditando que existe alguém ali naquele momento.
A trava de supervisão reduz, mas não elimina, nenhum dos dois.

---

## Custo da IA

Classificação em lote (até 12 mensagens por chamada) + cache do catálogo no
prompt. Uma live de 1h com chat movimentado fica na casa de poucos dólares com
`claude-opus-5`.

Se o volume crescer e o custo incomodar, troque no `.env`:

```
COPILOT_MODEL=claude-haiku-4-5
```

Classificação e resposta curta são tarefas em que o Haiku se sai bem por uma
fração do preço. Vale medir os dois numa live real antes de decidir.

---

## O que ainda não está pronto

Sendo direto sobre os buracos:

- **Vendas** — `vendas` e `receita` chegam zeradas. A API do TikTok Shop exige
  aprovação de partner app (semanas). Enquanto isso, a nota da live sai só do
  engajamento, e o catálogo é cadastrado à mão (ou por planilha) no painel.
- **Módulo de replay** — a infraestrutura de dados e a trava de supervisão estão
  prontas; falta o pedaço que joga o vídeo gravado no RTMP (OBS). Até lá, o
  comando `replay_live` vindo do painel volta marcado como `failed` e o log diz
  para reexibir manualmente pelo OBS.
- **Audiência** — `viewers_pico` e `viewers_media` ficam em zero: o `ingest.py`
  só escuta comentários, não os eventos de entrada/saída da live.
- **Cobrança** — sem Stripe. O multi-tenant por RLS já está no schema.
- **Recomendação de horário de live** — depende de histórico; só faz sentido
  depois de acumular umas 10 lives.
- **`seller_id` com default** — as tabelas de operação ainda carregam
  `default 'mix-conecta'`, herança da fase de loja única. Antes da segunda loja
  entrar, derrube esses defaults (o `schema.sql` traz o comando no rodapé).
