# TikTok AI Co-pilot

Copiloto de IA para vendedores de live commerce no TikTok. Lê o chat da live em
tempo real, classifica cada mensagem, sugere (ou envia) respostas, captura
WhatsApp e pontua leads.

Primeiro uso: Mix Conecta, para validar. Depois: SaaS a R$ 60/mês por vendedor.

## Como as peças se encaixam

```
PC do vendedor                    Nuvem                    Navegador
┌──────────────────┐         ┌─────────────┐         ┌──────────────┐
│ agent.py         │         │  Supabase   │         │ Painel       │
│                  │  write  │             │ realtime│ (Lovable)    │
│ TikTokLive ──────┼────────>│  messages   ├────────>│ Ao Vivo      │
│      ↓           │         │  leads      │         │ Lives Prontas│
│ Claude           │         │  lives      │         │              │
│      ↓           │  poll   │  commands   │  write  │ [Enviar]     │
│ Playwright ──────┼<────────┤             │<────────┤ [Reexibir]   │
└──────────────────┘         └─────────────┘         └──────────────┘
```

O agente roda **na máquina do vendedor** porque precisa de duas coisas que
navegador não faz: websocket do TikTok Live e controle do Chrome. O painel é web
e conversa com ele através do Supabase.

| Arquivo | Função |
|---|---|
| `agent.py` | Orquestrador. É o que você executa. |
| `ingest.py` | Lê o chat da live (biblioteca TikTokLive) |
| `ai.py` | Classifica em lote e redige as respostas (Claude) |
| `store.py` | Persistência — SQLite local ou Supabase |
| `sender.py` | Digita no chat via Playwright (ver aviso abaixo) |
| `catalog.py` + `products.json` | Catálogo de produtos, frete e prazos |
| `schema.sql` | Tabelas do Supabase |
| `LOVABLE_PROMPT.md` | Prompt pronto para gerar o painel |
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

Edite o `products.json` com os produtos reais da live. Esse arquivo vira o
contexto que a IA usa para responder — **preço errado aqui vira preço errado no
chat.**

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

`Ctrl+C` encerra e grava as métricas da live.

## Testes

```bash
python test_smoke.py
```

Cobre a captura de WhatsApp, a trava de auto-envio e o cálculo de avaliação da
live. Não precisa de API key nem de rede.

---

## Auto-envio no chat — leia antes de ligar

O TikTok **não tem API de envio de mensagem**. O `sender.py` automatiza a
interface web do LIVE Center com Playwright. Isso contraria os Termos de Uso e
pode levar a **banimento da conta**. Foi uma decisão consciente do dono do
projeto. Recomendação que continua valendo: **teste numa conta secundária
primeiro**, não na conta principal da loja.

Três travas, checadas antes de cada envio:

1. **Kill switch** — `AUTO_REPLY_ENABLED=false`, ou o botão PARAR TUDO no painel.
2. **Throttle** — `AUTO_REPLY_MAX_PER_MIN` (padrão 4), com intervalos aleatórios
   e digitação caractere a caractere. Cadência robótica é o que denuncia bot.
3. **Filtro de intenção** — só envia sozinho `preco`, `frete`, `prazo` e
   `como_comprar`. Reclamação, negociação e qualquer coisa que a IA marcou como
   `requires_human` vai para o vendedor. Sempre.

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

1. Crie o projeto no Supabase e rode o `schema.sql` inteiro no SQL Editor.
2. No `.env`, mude para `STORE_BACKEND=supabase` e preencha `SUPABASE_URL` e
   `SUPABASE_SERVICE_KEY` (a **service_role**, não a anon — o agente precisa
   passar por cima do RLS).
3. Crie o projeto no Lovable, conecte ao mesmo Supabase e cole o
   `LOVABLE_PROMPT.md`.

O painel tem duas páginas:

- **Ao Vivo** — chat, fila de respostas, leads quentes, coaching.
- **Lives Prontas** — biblioteca das lives gravadas, com nota (boa / regular /
  ruim), vendas por hora e recomendação de reexibir ou não.

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
  engajamento, e o `products.json` é preenchido à mão.
- **Módulo de replay** — a infraestrutura de dados e a trava de supervisão estão
  prontas; falta o pedaço que joga o vídeo gravado no RTMP (OBS).
- **Cobrança** — sem Stripe. O multi-tenant por RLS já está no schema.
- **Recomendação de horário de live** — depende de histórico; só faz sentido
  depois de acumular umas 10 lives.
