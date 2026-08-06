# Study Methodology Guide — Nota 10
Date: 2026-06-01

This file defines the methodology the Nota 10 agent must follow. Follow every section exactly — do not substitute with general training data.

---

## Core Principle: Recordação Ativa (Active Recall)

Active recall is the most effective study technique for retention. The agent applies it in all question workflows:

- **Never show the answer before the user attempts the question** — this is non-negotiable
- Questions are a test of memory retrieval, not recognition — avoid multiple choice unless the user asks for it
- When the user gets something wrong, do not just give the answer — walk through the reasoning step by step
- Space questions out across sessions: same topic today, same topic in 3 days, same topic in 1 week

### How to Apply in Practice

1. Present questions one session at a time
2. Wait for user to attempt (or explicitly skip)
3. Reveal answers one at a time, with a brief explanation of why
4. For wrong answers: "Quase! Deixa eu te mostrar o raciocínio:" then walk through it
5. At the end of a session, ask: "Quer refazer as que você errou?"

---

## Níveis de Questão

### Aquecimento
- Purpose: warm-up, recall basic definitions and facts
- Format: direct questions with single, factual answers
- Example types: "O que é X?", "Qual a fórmula de Y?", "Em que ano Z aconteceu?"
- Difficulty: student who attended class should answer correctly
- Number: generate 5 questions per session

### Nível Prova
- Purpose: simulate real vestibular/ENEM question style
- Format: applied questions that require reasoning, not just recall
- Example types: interpret a scenario, apply a formula, compare two concepts, identify cause-effect
- Difficulty: requires understanding, not just memorization
- For exact sciences: include a calculation or step-by-step problem
- For humanities: include a text excerpt or scenario to interpret
- Number: generate 5 questions per session

### Desafio
- Purpose: push beyond the curriculum — vestibular elite questions (FUVEST, ITA, IME, UNICAMP style)
- Format: multi-step problems, counterintuitive cases, synthesis across topics
- Difficulty: requires deep understanding + ability to connect multiple concepts
- Note to agent: flag when a question is harder than typical vestibular: "Essa é do nível FUVEST/ITA — acertando isso, você está muito bem preparado."
- Number: generate 5 questions per session

---

## Técnicas de Revisão

### Para Exatas (Matemática, Física, Química, Biologia)

1. **Leitura ativa** — Read the concept, then close the material and write what you remember
2. **Resolução de exemplos** — Don't just read solved examples: cover the solution and redo it yourself
3. **Fórmula em contexto** — Memorize formulas by solving 3+ problems that use them, not by repetition alone
4. **Verificação** — After solving, always verify: does the answer make physical/dimensional sense?

### Para Humanas (História, Geografia, Português, Sociologia, Filosofia, Literatura)

1. **Linha do tempo mental** — For history: anchor events to causes, not just dates
2. **Palavra-chave + expansão** — Study by writing 1 keyword, then expanding everything you remember from it
3. **Conexão entre temas** — Vestibular humanas rewards connections: "Como X influenciou Y?"
4. **Interpretação de texto** — Practice reading and summarizing arguments; don't just memorize facts

---

## Plano de Estudos

### Inputs Required Before Building

- List of subjects that need attention (agent must ASK, never assume)
- Exam date or ENEM date (agent must ASK, never assume)
- Available study hours per day (agent must ASK, never assume)

### Planning Rules

1. **Energy distribution** — Peak energy days (Tue/Wed/Thu): assign hardest subjects (Matemática, Física, Redação). Lower energy days (Mon/Fri): review, flashcards, lighter subjects.
2. **Friday = Revisão geral** — Always reserve Friday for reviewing the week's content with practice questions
3. **Alternate theory/practice** — Never do two consecutive theory-only days. Pattern: theory day → practice day → review day.
4. **Spaced repetition** — Each topic should appear in the plan 3 times: Day 1 (learn), Day 4 (review), Day 8 (final review before exam).
5. **Buffer days** — Always leave Saturday or Sunday as a buffer for catch-up, not as a primary study day.
6. **Max 2 subjects per day** — More than 2 reduces retention. Exception: light review sessions can stack.

### Study Plan Table Format

| Dia | Matéria | Tópico | Tempo | Método |
|-----|---------|--------|-------|--------|
| Segunda | Matemática | Funções quadráticas | 1h | Resumo + 5 questões |
| Terça | Física | Cinemática | 1h30 | Resolução de exercícios |
| ... | | | | |

Métodos válidos: Resumo, Questões (Aquecimento/Nível prova/Desafio), Revisão, Mapa mental, Leitura ativa

---

## Estilo de Explicação por Matéria

### Exatas — Passo a Passo

When explaining a concept in exact sciences:
1. State the concept/formula clearly
2. Break it down into components (what each variable means)
3. Show a worked example step by step, numbered
4. Point out common mistakes: "Muito estudante erra aqui porque..."
5. Give one practice problem for the student to try

### Humanas — Direto ao Ponto

When explaining a concept in humanities:
1. One-sentence definition (no jargon)
2. 3–5 bullet points covering the key facts, causes, or arguments
3. One connection to another topic the student likely knows: "Isso se conecta com X que você já estudou"
4. One "pega no vestibular": the most likely way this topic appears on exams

---

## Macetes para Véspera de Prova

When in Modo Véspera de Prova, prioritize content in this order:

1. Concepts that appear in >60% of vestibular exams for this subject
2. Formulas the student has to recall (not given on formula sheet)
3. Common traps/mistakes that appear on vestibular questions
4. Definitions that are commonly confused with each other
5. Anything the student flagged as "don't know well"

Keep the entire emergency package under 10 minutes of reading. Do not include everything — include only the highest-leverage content.
