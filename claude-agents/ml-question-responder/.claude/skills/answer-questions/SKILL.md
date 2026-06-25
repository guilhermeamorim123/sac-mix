---
name: answer-questions
description: Run the full ML question-answering cycle — fetch pending buyer questions from all configured accounts, analyze sentiment, generate persuasive responses, post automatically when confident, escalate otherwise.
argument-hint: "[--dry-run]"
user-invocable: true
allowed-tools: Bash, Read, Write, Edit, WebSearch
---

# Answer Questions Skill

Run the complete Mercado Livre question-answering cycle.

## Arguments

- (no args) — run full cycle and post approved answers
- `--dry-run` — process and generate responses but DO NOT post; show all drafts for review

## Workflow

Follow these steps in order. Do NOT skip steps.

### Step 1 — Load guidelines
Read `context/answer-guidelines.md` fully before processing any question.

### Step 2 — Fetch pending questions (all accounts)
Run for each account index N = 1, 2, ... until no token found:
```bash
python scripts/get_questions.py --account N
```
Collect all returned questions into a working list. If no questions found on any account, report "Nenhuma pergunta pendente" and stop.

### Step 3 — Process each question
For each question in the working list:

**3a. Fetch item data**
```bash
python scripts/get_item.py --item-id ITEM_ID
```

**3b. Analyze sentiment**
Read the question text and classify: curioso / cético / urgente / sensível_a_preço / animado.
State your classification and reasoning in one sentence before drafting.

**3c. Check escalation triggers**
If question mentions any of: preço / desconto / negociação / devolução / troca / reembolso / defeito / reclamação / garantia / ameaça / processo / Procon / Reclame → mark ESCALATE immediately, skip to 3h.

**3d. Evaluate confidence**
Score 0–100 based on whether item attributes and description directly answer the question.
- ≥ 90 → proceed to 3e (draft response from ML data)
- < 90 → proceed to 3f (WebSearch fallback — do NOT escalate)

**3e. Draft persuasive response**
Use the sentiment strategy and template from answer-guidelines.md:
1. Empathy opening aligned to sentiment
2. Direct, factual answer (data from API only)
3. Benefit-chave relevant to the question
4. Soft CTA appropriate to confidence level

If `--dry-run`: show draft, do NOT call post_answer.py. Continue to next question.

If NOT `--dry-run`:
```bash
python scripts/post_answer.py --question-id QUESTION_ID --text "RESPONSE_TEXT" --account N
```
Then append to log:
```bash
# Append to logs/YYYY-MM-DD.md (create if needed)
```

Log entry format:
- ML-sourced answer: `- [HH:MM] Q#QUESTION_ID — Item ITEM_ID — [ML] — [sentimento] — resposta postada`
- Web-sourced answer: `- [HH:MM] Q#QUESTION_ID — Item ITEM_ID — [WEB] — [sentimento] — resposta postada`

Append to `logs/YYYY-MM-DD.md` (create file with header `# Log YYYY-MM-DD\n` if it doesn't exist).

**3f. WebSearch fallback**
Chegou aqui porque a confiança nos dados do anúncio foi < 90% e o tópico não é bloqueado.

Construa a query: `"[title do anúncio] [especificação perguntada]"` — em português.

Execute WebSearch com essa query. Avalie até 3 resultados conforme as regras em `context/answer-guidelines.md` seção "Busca Web".

- Resultado aceito → use o dado encontrado para redigir a resposta em 3e (volte ao Step 3e usando o dado web como fonte; aplique a lógica de `--dry-run` normalmente; use a tag `[WEB]` no log)
- Nenhum resultado aceito → vá para 3g

**3g. Generic response**
Nenhuma fonte (anúncio ML nem web) tem o dado. Poste a resposta genérica padrão:

If `--dry-run`: show the generic text below but DO NOT call post_answer.py. Log entry still applies.

```bash
python scripts/post_answer.py --question-id QUESTION_ID --text "Olá! Para mais detalhes sobre essa especificação, recomendo entrar em contato pelo chat do Mercado Livre — assim consigo te ajudar com mais precisão. 😊" --account N
```

Append to log:
```
- [HH:MM] Q#QUESTION_ID — Item ITEM_ID — [GENÉRICA] — Dado não encontrado em anúncio nem na web
```

**3h. Escalate** *(apenas tópicos bloqueados — vindo do Step 3c)*

Append em `pending-questions.md`:
```
## [YYYY-MM-DD HH:MM] Conta N — Item ITEM_ID
**Pergunta:** [question text]
**Motivo escalada:** [tópico bloqueado: preço/devolução/defeito/garantia/legal]
**Link:** https://www.mercadolivre.com.br/...
```

### Step 4 — Summary
Display at the end:
```
✅ Respondidas (anúncio ML): X
🔍 Respondidas (busca web): W
💬 Resposta genérica postada: V
⏳ Escaladas para revisão humana: Y
📋 Contas processadas: Z
```

## Edge Cases

- API error on get_questions → report error, skip account, continue others
- API error on post_answer → mark question as ESCALATE with reason "Erro ao postar via API"
- Item has no description → confidence automática = 40%, vai para WebSearch (3f)
- Question is in English or Spanish → respond in Portuguese anyway
- `pending-questions.md` does not exist → create it with header `# Perguntas Pendentes\n`
