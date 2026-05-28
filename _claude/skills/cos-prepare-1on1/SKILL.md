---
name: cos-prepare-1on1
description: Inicia preparação interativa para 1:1 com um membro do time
user-invocable: true
argument-hint: <member-name>
effort: medium
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

Iniciar preparação interativa para one-on-one com $ARGUMENTS.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

IMPORTANT: This is a conversation, not a report. Start with Phase 1 (Intent). Do NOT build the full briefing before asking the owner what they want to focus on.

## Scope

1:1 preps focus on **people and development**, NOT on project-specific task demands or bypass incidents. O gestor tem reuniões semanais dedicadas per project (e.g., a weekly per project) to cover task-level details, deadlines, and technical demands.

**IN scope for 1:1 preps:**
- Recognition and positive reinforcement
- Behavioral feedback (communication, accountability, initiative)
- Development plan progress and Q2 goals
- Engagement signals and trend analysis
- Career conversations and aspirations
- Personal check-ins
- Cross-cutting patterns (e.g., ClickUp discipline, recurring items)
- Coaching approach for difficult conversations

**OUT of scope for 1:1 preps (covered in project weeklies):**
- Specific project task lists and action item status from project weeklies
- Technical demands, deadlines per feature, or blocker details of individual projects
- Bypass incidents (a stakeholder going directly to a member, etc.) — a menos que o gestor sinalize explicitamente as a topic

**Exception:** If a project topic has a clear **behavioral/people angle** (e.g., "pausou sem comunicar" = accountability conversation), include the behavioral angle in the briefing but NOT the task-level details.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped.

**Pre-flight**
0. **Load config + integration availability** — read `context/cos-config.md`, resolve tokens, enable/skip integrations per config

**Phase 1 — Intent**
1. **calendar check** — verify if 1:1 is scheduled
2. ⏸️ **PAUSE: Ask intention** — o que o gestor quer focar

**Phase 2 — Collect** (Core → Dep Analysis → Targeted)
3. **Load Core context** — spawn parallel agents for profile, dev-plan, last meeting, o gestor, decisions, references
4. **Dependency Analysis** — analyze Core results, extract targeted scope from profile data
5. **Load Targeted context** — spawn parallel agents for projects, extra profiles, comms, tasks, Calendar
6. 🔍 **Quality gate: source completeness** — verify all sources consulted

**Phase 3 — Analyze & Present**
9. **Run management lens** — internal analysis enriching provocations
10. **Build directed briefing** — 4 blocks oriented by a intenção do gestor
11. 🔍 **Quality gate: briefing quality** — verify depth and management lens
12. ⏸️ **PAUSE: Present briefing** — wait for o feedback do gestor
13. **Incorporate feedback** — adjust with o input do gestor

**Phase 4 — Save**
14. **Save prep file** — write with frontmatter to meeting folder
15. **calendar sync** — create/update event if needed
16. **Confirm save** — report path, offer audio processing later

**Phase 5 — Propagate & Close**
17. 🔍 **Propagation: build manifest** — scan conversation for new info
18. **Propagate** — parallel agents if items exist
19. **Wrap-up** — confirm everything done

## Process

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill uses integrations: **slack, clickup, calendar** (plus always-on vault and references).

- Resolve all `{{...}}` tokens from the config "Integration IDs" table.
- Toggle `false` → skip that integration's calls; `true` → test MCP, skip-with-warning if unavailable.
- Never stop the prep for a missing integration. Vault data (member profile, last 1:1 record, pendings) always drives a usable prep.
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-first.

### Step 1 — calendar check

**(Only if capability `calendar` is configured)** Before asking anything, query the `calendar` MCP:

1. Search for scheduled 1:1 with this member (today or upcoming days) using `list_events`
2. If found: note date, time, duration, location/meet link
3. If NOT found: note this — may need to create event later

Present: "Sua 1:1 com [nome] está agendada para [dia] às [hora] ([duração]min)." or "Não encontrei 1:1 com [nome] no calendar. Quer que eu crie depois de preparar?"

Se a capability `calendar` não estiver configurada, pergunte ao usuário o horário da reunião em vez de consultar a agenda: "Qual o horário da sua 1:1 com [nome]?"

### Step 2 — ⏸️ PAUSE: Ask intention

Before reading any data, usar AskUserQuestion:

```
Question 1: "Qual seu objetivo pra essa 1:1 com [nome]?"
Options:
- "Acompanhar entregas" — foco em tasks, deadlines, blockers
- "Desenvolvimento/feedback" — foco em crescimento, competências, feedback pendente
- "Tema sensível" — preciso preparar abordagem cuidadosa
- "Check-in geral" — sem tema específico, vou direcionar pelos dados

Question 2: "Tem algo específico que quer abordar?"
→ Plain text (open-ended — espaço aberto)
```

**Wait for the owner's response before proceeding.**

Se o gestor disser "não sei" or is vague → proceed to data collection, then suggest: "Pelos dados, sugiro focar em [X]. O que acha?"

### Step 3 — Load context (Core → Dep Analysis → Targeted)

**Phase A — Core (parallel agents):**

Pre-calculate Unix timestamps in main thread:
- `seven_days_ago`: Unix timestamp for 7 days ago

Spawn agents in parallel using the dedicated CoS loader agents (each declares its own MCPs and tools via frontmatter):

**Agent 1 — Core vault** (`subagent_type: cos-vault-loader`):
- Read `team/$ARGUMENTS/<First Last>.md` — member profile (personal info, notes, communication style)
- Read `team/$ARGUMENTS/<First Last> dev-plan.md` — development plan (competencies, progress, stagnation)
- Read last 1 meeting record from `team/$ARGUMENTS/meetings/` (most recent `YYYY-MM-DD 1on1 *.md`, NOT transcription.txt)
- Read `team/<owner-slug>/<Owner Name>.md` — as prioridades do gestor, focus areas
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — as competências de gestão do gestor
- Read `context/decisions.md` — filter for decisions involving this member
- Return: member state, dev plan status, last meeting action items + engagement scores, as áreas de foco do gestor + management competencies, relevant decisions

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `docs/reference/integrations.md` — task routing rules, IDs, statuses, comms channel IDs
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming
- Return: routing rules, convention rules, channel IDs

**Phase B — Dependency Analysis (main thread):**

Analyze Core results. From the member profile (current projects, notes) and last meeting record (open action items, topics), extract:
- Active projects → load their context files
- People mentioned in notes or last meeting → load their profiles
- Unresolved items from last meeting → flag for agenda
- task projects to query → focus agent scope

**Phase C — Targeted (parallel agents, only if deps have items):**

**Agent 3 — Targeted vault** (`subagent_type: cos-vault-loader`):
- Project context files for member's active projects (from Phase B)
- Profiles of people related to member's work (from Phase B)
- Additional meeting records if unresolved items suggest history needed

**(Only if capability `comms` is configured)** **Agent A — comms** (`subagent_type: cos-mcp-loader`):
Include in prompt: `#time` = `<team channel from comms MCP details>`, `#projetos` = `<projects channel from comms MCP details>`.

Base:
- `read_channel` `<team channel from comms MCP details>` (oldest: `seven_days_ago`)
- `read_channel` `<projects channel from comms MCP details>` (oldest: `seven_days_ago`)
- `search_public` `from:@member "blocked" OR "stuck" OR "problema" OR "help" after:YYYY-MM-DD` — blocker signals

Targeted:
- If Phase B identified specific project discussions: targeted search
- Thread expansion only for relevant topics
- No DM reads (targeted only if profile indicates private conversation needed)

Extract and classify: notable contributions, engagement signals, personal signals, unusual silence, behavioral patterns (communication gaps, initiative, accountability).
- Do NOT deep-dive into project-specific task progress — that belongs in project weeklies
- Return: classified comms intelligence focused on people/behavioral signals

**(Only if capability `tasks` is configured)** **Agent B — tasks** (`subagent_type: cos-mcp-loader`):
Include in prompt: Space `<workspace id from tasks MCP details>`.
- Tasks assigned to this member (active statuses, overdue, blocked)
- If Phase B identified projects: tasks in those projects

**(Only if capability `calendar` is configured)** **Agent C — calendar** (`subagent_type: cos-mcp-loader`):
Include in prompt: timezone `<timezone from calendar MCP details>`, member email.
- Upcoming events involving this member (next 14 days)
- Verify scheduled 1:1 exists

Consolidate all results before proceeding.

### Step 4 — 🔍 Quality gate: source completeness

After all agents return, verify each source was consulted:

□ Member profile loaded?
□ Member dev-plan loaded?
□ Last meeting record loaded?
□ o perfil do gestor + dev-plan loaded?
□ tasks for this member consulted?
□ context/decisions.md filtered for this member?
□ comms: channel reads completed (#time, #projetos)?
□ comms: blocker search completed?
□ calendar: upcoming events checked?
□ Targeted: project context files loaded (if applicable)?

If any source failed → retry once. If still unavailable → note in briefing: "⚠️ [source] indisponível — briefing pode estar incompleto nesta dimensão."

### Step 5 — Run management lens

Internal analysis — NOT shown as raw checklist to o gestor. Enriches Blocks 3 and 4 of the briefing.

**COACHING STYLE TRAJECTORY:**
- From last 3 meeting records: count Coaching / Directing / Solving moments
- Tendência: o gestor está fazendo mais ou menos coaching ao longo do tempo?
- If predominantly Directing/Solving → suggest coaching approach for this meeting

**DEVELOPMENT PLAN HEALTH:**
- How long since dev-plan was last updated?
- Any competency stagnant for 2+ months?
- Any target competency that could be practiced in this meeting?

**ENGAGEMENT TRAJECTORY:**
- From last 3 meetings: plot Mood, Motivation, Workload, Satisfaction trends
- Any dimension dropping consistently? → flag for Block 3
- Any dimension high for 3+ meetings? → recognize

**WILL'S COMMITMENTS:**
- From last meeting: what did o gestor commit to?
- Which are fulfilled vs unfulfilled?
- Unfulfilled → MUST appear in Block 1 (Pendências)

**WILL'S MANAGEMENT PRACTICE:**
- From do gestor dev-plan: which competency is he working on?
- Can this 1:1 be an opportunity to practice it?
- Suggest specific moment/approach in Block 4

**BLIND SPOTS:**
- Topics NOT discussed in last 3 meetings (personal life, career goals, specific project, specific competency)
- If 3+ meetings without personal check-in → flag
- If dev-plan not referenced in 2+ meetings → flag

### Step 6 — Build directed briefing

Present briefing in 4 blocks, **oriented by a intenção declarada from Step 2**:

**Block 1: Pendências**
- Action items from last meeting with real status (Done / In Progress / Not Started)
  - Cross-reference with task status when available
  - If item is recurring (3+ meetings): mark ⚠️ RECORRENTE with suggested approach
- os próprios compromissos do gestor from prior meetings: flag if unfulfilled ("Você se comprometeu com [X]. Foi feito?")
- Decisions from context/decisions.md that impact this member: check if implementation has been discussed
- Overdue tasks assigned to this member

**Block 2: Pauta Sugerida**
- Topics aligned with a intenção declarada (from Step 2)
- Topics Claude identifies as necessary mesmo que o gestor não tenha mencionado:
  - Behavioral patterns requiring feedback (accountability, communication, initiative)
  - Engagement signals from the `comms` MCP (frustration, silence, notable contributions)
  - Dev-plan items due for review or formalization
  - Decisions pending that impact the member's role or growth
  - Cross-cutting discipline issues (e.g., tasks hygiene, recurring items)
- **Exclude:** specific project task lists, feature-level deadlines, technical blockers — those belong in project weeklies
- Prioritized: behavioral feedback → development → engagement → general check-in
- Time estimate per topic if meeting has known duration

**Block 3: Provocações** (enriched by management lens)
- Questions o gestor should ask but might not think of
- Blind spots: topics NOT addressed in last 3 meetings
  - "Faz X reuniões que você não pergunta sobre [carreira / vida pessoal / desenvolvimento técnico]. Considere incluir."
- Engagement trend analysis: "Os últimos scores mostram [tendência]. Quer explorar o porquê?"
- Dev-plan staleness: "Nenhum progresso registrado em [competência] nos últimos X meses."
- Coaching style nudge: "Nas últimas 3 reuniões, seu estilo foi predominantemente [Directing]. Quer tentar uma abordagem mais Coaching nesta?"
- a competência de gestão do gestor: "Oportunidade de praticar [competência do dev-plan] quando abordar [tópico]."
- comms intelligence: notable contributions to recognize, unusual silence, engagement signals (NOT bypass details — those are for project weeklies unless o gestor sinalizou it)

**Block 4: Coaching de Abordagem**
- If there's a difficult topic: suggested script using SBI framework adapted to the member's communication style (from profile)
- If there's positive feedback pending: remind o gestor to recognize (specific achievements from the `comms` MCP/ClickUp)
- If engagement is dropping: strategy for exploring without being confrontational
- If it's a first meeting after long gap: suggest re-connection topics
- If a competência do dev-plan do gestor can be practiced: specific suggestion for when and how
- Se o gestor pediu "Tema sensível" in Step 2: detailed approach script:
  - Opening (empathetic, acknowledge what's going well)
  - Transition (connect to the issue)
  - Facts presentation (SBI, no judgment)
  - Listening questions (explore their side)
  - Co-creation (define expectations together)
  - Closing (reinforce trust)

### Step 7 — 🔍 Quality gate: briefing quality

Before presenting, verify:

□ All 4 blocks present (Pendências, Pauta, Provocações, Coaching)?
□ Pendências include real status per action item (not generic "em andamento")?
□ do gestor unfulfilled commitments flagged?
□ Pauta aligned with a intenção declarada from Step 2?
□ Provocações include at least 1 management lens insight (coaching style, dev-plan, engagement, blind spots)?
□ Action items recurring 3+ times flagged with ⚠️ RECORRENTE?
□ Blind spots identified (topics absent from last 3 meetings)?
□ Coaching section includes approach strategy if sensitive/difficult topic exists?
□ comms intelligence surfaced (engagement signals, contributions, behavioral patterns)?

If any item fails → fix before presenting. Do NOT present an incomplete briefing.

### Step 8 — ⏸️ PAUSE: Present briefing

Apresentar os 4 blocos ao gestor. After presenting, use AskUserQuestion:

```
Question 1: "Como ficou a preparação?"
Options:
- "Boa, salvar" — aprovar e salvar prep file
- "Ajustar pauta" — modificar ordem ou prioridade dos tópicos
- "Adicionar tópico" — incluir algo que não apareceu
- "Mudar abordagem" — repensar o coaching/approach

Question 2 (if ⚠️ RECORRENTE items detected):
"Item '[X]' aparece pela Xª vez. Como quer abordar?"
Options:
- "Cobrar diretamente" — endereçar na reunião com expectativa clara
- "Escalar" — tratar como performance issue
- "Redefinir" — talvez o item não faça mais sentido
- "Remover" — não é mais relevante
```

Ask as many questions as needed. **Wait for the owner's response before proceeding.**

Any positive acknowledgment from o gestor ("boa", "ok", "vamos", "boa preparação", "bora", or moving on to another topic) counts as approval → proceed immediately to save.

### Step 9 — Incorporate feedback

- Apply os ajustes do gestor to the briefing
- Se o gestor adicionar novos tópicos or context → note for propagation gate later
- Se o gestor compartilhar novas informações about the member (concerns, plans, strategy) → note for propagation

### Step 10 — Save prep file

Create meeting folder if it doesn't exist: `team/<member>/meetings/YYYY-MM-DD/`

Write `YYYY-MM-DD prep 1on1 <FirstName>.md` with YAML frontmatter:

```markdown
---
type: prep
subtype: 1on1
date: YYYY-MM-DD
participant: "[[Full Name]]"
status: completed
tags:
  - prep/1on1
---

# Preparação 1:1 — [[Full Name]] — YYYY-MM-DD

## Objetivo da Reunião
[a intenção declarada from Step 2]

## Pendências
[Block 1 — action items with real status, recurrence flags, os compromissos do gestor]

## Pauta
[Block 2 — prioritized agenda items aligned with intention]

## Provocações
[Block 3 — management lens insights, blind spots, engagement trends, dev-plan prompts]

## Coaching de Abordagem
[Block 4 — scripts, strategies, recognition reminders]

---
**See also:** [[Full Name]] | [[Full Name dev-plan]] | [[MOC Meetings]]
```

### Step 11 — calendar sync

- If 1:1 is NOT on calendar: use AskUserQuestion:
  ```
  "1:1 com [nome] não está no calendar. Criar evento?"
  Options:
  - "Sim, sugerir horários" — query both calendars, present options
  - "Não, já está combinado" — skip
  - "Criar com horário específico" — o gestor fornece o horário
  ```
  If approved: create event via `create_event` with title, description (agenda highlights), attendees
- If 1:1 IS on calendar: offer to update event description with agenda from prep file. Wait for approval.

### Step 12 — Confirm save

Report to the owner:
- "Preparação salva em `team/<member>/meetings/YYYY-MM-DD/YYYY-MM-DD prep 1on1 <FirstName>.md`."
- Calendar status: created/updated/skipped
- "Boa reunião! Depois me manda o áudio que eu processo."

### Step 13 — 🔍 Propagation: build manifest

Scan the ENTIRE conversation for distributable information from o input do gestors during Steps 2, 8-9. Look for:

- **Decisions made** — strategy shifts, priority changes, escolhas ad-hoc que o gestor compartilhou
- **People info** — new context about the member or others mentioned
- **Project updates** — status changes, new risks, reprioritization
- **as prioridades do gestor** — focus changes mentioned during intent or feedback
- **Pendings** — things that surfaced as needed but unresolved

**Deduplication:** Skip anything already captured in the prep file itself. Focus on info que o gestor compartilhou na conversa that goes beyond the prep content.

Build manifest with: item description, category, destination file, action (new/update/skip).

**If nothing to propagate** → skip Step 14, go directly to wrap-up.

### Step 14 — Propagate (parallel agents if items exist)

Spawn agents using `cos-vault-loader` (extended with Write/Edit) per category with items:

- **People Agent** (`subagent_type: cos-vault-loader`): Update profiles in `team/` or `people/` with new info
- **Projects Agent** (`subagent_type: cos-vault-loader`): Update project context files with new status/risks
- **Context Agent** (`subagent_type: cos-vault-loader`): Update context/decisions.md, team.md, pendings.md, o perfil do gestor/dev-plan

Only spawn agents for categories with actual work. Main thread verifies results.

### Step 15 — Wrap-up

Report to the owner:
- Prep file saved: path
- calendar: status
- Propagated: list of files updated (if any)
- "Boa reunião! Depois me manda o áudio que eu processo."

## Edge Cases

- **First meeting with this member**: No meeting history — focus on getting to know the person. Skip Block 1 (Pendências). Suggest discovery questions in Block 3: personal interests, career goals, work expectations, communication preferences. Block 4: "how to build rapport" approach
- **Urgent meeting** (crisis, performance issue): Skip Step 2 intent-setting — a intenção do gestor is clear. Go directly to focused briefing on the urgent topic. Block 4 becomes primary focus with detailed approach script
- **O gestor não tem objetivo claro**: Proceed to data collection, then suggest focus: "Pelos dados, as 3 coisas mais relevantes pra discutir com [nome] são: [list]. Qual ressoa mais?"
- **Member with declining engagement**: Lead Block 3 with engagement analysis. Suggest specific exploratory questions. Block 4: strategy for exploring without confrontation
- **Very recent last meeting** (<7 days): Focus on follow-up of recent items. Lighter briefing — skip deep management lens, focus on "algo mudou desde a última conversa?"
- **No comms activity from member** (unusual silence): Flag in Block 3 as potential signal. "Nenhuma atividade no Slack nos últimos X dias. Normal para [nome]?"
- **Multiple overdue tasks**: Prioritize in Block 2. Block 4: approach for accountability conversation without micromanaging

## Quality Rules

- **Intent first, data second** — NEVER build the briefing before understanding o que o gestor quer. The data serves the intention, not the other way around
- **Provocations must provoke** — generic "pergunte como ele está" is worthless. Every provocation must be grounded in data (engagement scores, dev-plan staleness, Slack signals, recurrence patterns)
- **os compromissos do gestor são sagrados** — se o gestor prometeu something to the member and didn't deliver, it MUST appear in Block 1. No exceptions, no softening
- **Recurrence tracking is mandatory** — items appearing 3+ consecutive meetings get ⚠️ RECORRENTE with suggested escalation approach
- **Factual comms intelligence** — report what was observed (messages, patterns, silence), not interpretations. Let the owner interpret
- **Save is mandatory** — the workflow is NOT complete until the prep file is written. Any form of positive acknowledgment triggers save immediately
- **Scope discipline** — 1:1 preps are about PEOPLE, not projects. If a topic is purely about task status or technical demands, it belongs in the project weekly. Only include project-related items when they reveal a behavioral/people angle (accountability, communication, initiative). Do NOT include bypass incidents a menos que o gestor sinalize explicitamente
- **Wikilinks always** — `[[Full Name]]` for people, `[[Project Display Name]]` for projects in all files

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Member profile: `team/$ARGUMENTS/<First Last>.md`
- Dev plan: `team/$ARGUMENTS/<First Last> dev-plan.md`
- Last meetings: most recent `YYYY-MM-DD 1on1 *.md` in `team/$ARGUMENTS/meetings/`
- o perfil do gestor: `team/<owner-slug>/<Owner Name>.md`
- o dev-plan do gestor: `team/<owner-slug>/<Owner Name> dev-plan.md`
- Decisions: `context/decisions.md`

If the briefing was built but not saved, re-apresentar ao gestor para confirmação before saving.
If the briefing was saved, proceed to propagation and wrap-up.
