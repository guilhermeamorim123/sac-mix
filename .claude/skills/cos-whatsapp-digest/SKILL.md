---
name: cos-whatsapp-digest
description: Use when the owner wants to review recent WhatsApp messages and prepare responses based on their communication style
user-invocable: true
allowed-tools: Read, AskUserQuestion, list_chats, list_messages, send_message, search_contacts
---

# WhatsApp Digest

Lê as 10 conversas mais recentes do WhatsApp, mostra o que está pendente de resposta e prepara rascunhos no estilo do Guilherme.

**REGRA DE OURO: NUNCA enviar mensagens sem aprovação explícita.** Sempre mostrar rascunhos antes de enviar qualquer coisa.

## Checklist

1. Carregar estilo de comunicação do dono
2. Buscar as 10 conversas mais recentes
3. Buscar contexto das conversas pendentes de resposta
4. Apresentar resumo
5. ⏸️ PAUSE — perguntar orientações
6. Rascunhar respostas
7. ⏸️ PAUSE — aprovação antes de enviar
8. Enviar mensagens aprovadas

## Processo

### Step 0 — Carregar perfil

Leia `team/guilherme-figueredo/Guilherme Figueredo.md` para absorver:
- Estilo de comunicação: direto, curto, objetivo, sem enrolação
- Contexto e prioridades atuais

### Step 1 — Buscar conversas recentes

Chame `list_chats` com:
- `limit: 10`
- `sort_by: "last_active"`
- `include_last_message: true`

Para cada conversa, classifique:
- **🔴 Aguardando resposta** — `last_is_from_me` é `false` (outra pessoa enviou a última mensagem)
- **✅ Já respondido** — `last_is_from_me` é `true` (o dono enviou a última mensagem)

### Step 2 — Buscar contexto das pendentes

Para cada conversa classificada como 🔴:
- Chame `list_messages` com `chat_jid`, `limit: 5`, `sort_by: "newest"`
- Isso dá contexto suficiente para entender o assunto e a última mensagem recebida

### Step 3 — Apresentar resumo

Mostre uma tabela com as 10 conversas:

```
| # | Contato | Última mensagem (resumida) | Hora | Status |
|---|---------|---------------------------|------|--------|
| 1 | João    | "Quando fica pronto?"     | 14h32| 🔴 Aguardando |
| 2 | Mamãe   | "Ok! 👍"                  | 13h15| ✅ Respondido |
```

Para as 🔴, mostre abaixo da tabela um resumo rápido de cada conversa:
> **João** — Perguntando sobre prazo de entrega de um produto. Última mensagem há 2h.

### Step 4 — ⏸️ PAUSE: Orientações

Use `AskUserQuestion`:

```
Pergunta: "Quer que eu prepare respostas para as conversas pendentes?"
Opções:
- "Sim — responde tudo que tá pendente"
- "Sim — vou te dizer quais"
- "Não por agora"
```

Se "Sim — vou te dizer quais": peça quais (pelo número da tabela) e se tem alguma orientação específica (ex: "fala que to ocupado", "combina pra amanhã cedo", "pede o comprovante").

Se "Não por agora": PARE. Informe: "Digest feito. X conversa(s) pendente(s) de resposta."

### Step 5 — Rascunhar respostas

Para cada conversa selecionada, redija uma resposta seguindo estas regras:

**Estilo:**
- pt-BR, casual, como Guilherme escreveria — direto, sem formalidade
- Curto: 1-3 frases no máximo, a não ser que a situação exija mais
- Abreviações naturais ok (vc, tá, pq, né, etc.)
- Sem saudações excessivas se já é uma conversa em andamento

**Conteúdo:**
- Baseado nas últimas mensagens da conversa + orientação do dono
- Se a orientação for vaga ("responde qualquer coisa"), inferir uma resposta coerente com o contexto
- Se a mensagem tiver mídia (foto, áudio) sem descrição → indicar na resposta que você viu ou pergunte ao dono o que responder

### Step 6 — ⏸️ PAUSE: Aprovação

Apresente todos os rascunhos com contexto:

```
---
💬 João (última: "Quando fica pronto?")
Rascunho: "Oi João! Amanhã de tarde fica pronto, qualquer coisa te aviso"

💬 Maria (última: "Pode me ligar?")
Rascunho: "Oi Maria! Pode sim, mas não agora. Te ligo às 16h"
---
```

Use `AskUserQuestion`:
```
Pergunta: "Posso enviar essas mensagens?"
Opções:
- "Envia tudo"
- "Quero ajustar alguma"
- "Cancela tudo"
```

Se "Quero ajustar alguma": pergunte qual e o que mudar, atualize o rascunho, mostre de novo, repergunte a aprovação.

**NUNCA avance para o Step 7 sem aprovação explícita aqui.**

### Step 7 — Enviar

Para cada mensagem aprovada:
- Chame `send_message` com `recipient: chat_jid` e o texto aprovado
- Confirme cada envio: "✅ Enviado para [Nome]"

Se algum envio falhar: informe o erro e pergunte se quer tentar de novo.

### Relatório final

"Digest concluído. X enviada(s), Y pendente(s) de resposta."

## Regras

- **NUNCA enviar sem aprovação** — sem exceção, mesmo que o dono tenha dito "pode mandar tudo" antes do Step 6
- **Não inventar contexto** — usar apenas o que as mensagens mostram
- **Manter o estilo do Guilherme** — curto, direto, sem enrolação, sem formalidade desnecessária
- **Grupos**: tratar como qualquer chat. Se for grupo, indicar "(grupo)" no nome na tabela
- **Mídia sem contexto**: indicar `[foto]`, `[áudio]`, `[documento]` no resumo — não tentar descrever o que não foi transcrito
- **MCP indisponível**: se `list_chats` falhar → informar "WhatsApp MCP não acessível. Verifique se o bridge está rodando (`whatsapp-bridge/`)." e parar
