---
name: cos-prepare-weekly
description: Inicia preparação interativa para a weekly do time
user-invocable: true
effort: medium
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

Iniciar preparação interativa para weekly do time.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

IMPORTANT: Start with Phase 1 (Intent). Present the snapshot first, then ask before building the full agenda. Do NOT dump the entire briefing at once.

## Scope & Format

**Target duration: 15 minutes.** The weekly is a general team sync, NOT a project deep-dive.

O gestor tem **dedicated weekly meetings per project** (e.g., Weekly {{PROJECT_NAME_A}}, Weekly {{PROJECT_NAME_B}}) to cover task-level details. The team weekly should focus on:

**IN scope:**
- Team health and pulse (who's thriving, who's struggling)
- Quick status per member (1-2 sentences, not task lists)
- Cross-cutting alerts (overdue patterns, engagement drops, stagnation)
- Recognitions and wins
- 1-2 strategic decisions that need the whole team
- Quick blockers that need visibility
- Dev-plan nudges (stagnant competencies)

**OUT of scope:**
- Per-project task lists and feature-level status
- Technical deep-dives on individual projects
- Detailed action item review per project (covered in project weeklies)
- Bypass incidents (handle in 1:1s)

**Format discipline:** Every agenda topic should fit in ~2-3 minutes. If a topic needs more than 3 minutes, it probably belongs in a dedicated meeting. Flag it as "needs dedicated time" instead of expanding the weekly.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped.

**Pre-flight**
0. **Load config + integration availability** — read `context/cos-config.md`, resolve tokens, enable/skip integrations per config

**Phase 1 — Intent**
1. **calendar check** — verify if weekly is scheduled
2. ⏸️ **PAUSE: Ask intention** — o que o gestor quer comunicar ou decidir

**Phase 2 — Collect** (Core → Dep Analysis → Targeted)
3. **Load Core context** — spawn parallel agents for all profiles, last weekly, o gestor, decisions, references
4. **Dependency Analysis** — analyze Core results, identify flagged members and active projects
5. **Load Targeted context** — spawn parallel agents for dev-plans, project contexts, comms, tasks, Calendar
6. 🔍 **Quality gate: source completeness** — verify all sources consulted for all members

**Phase 3 — Analyze & Present**
9. **Run team dynamics lens** — internal analysis enriching provocations
10. **Build snapshot** — action items by owner, project status, alerts
11. **Build strategic agenda** — prioritized topics + provocations
12. 🔍 **Quality gate: briefing quality** — verify per-member completeness and team lens
13. ⏸️ **PAUSE: Present briefing** — snapshot + agenda, wait for o feedback do gestor
14. **Incorporate feedback** — adjust with o input do gestor

**Phase 4 — Save**
15. **Save prep file** — write with frontmatter to weeklys folder
16. **calendar sync** — create/update event if needed
17. **Confirm save** — report path, offer audio processing later

**Phase 5 — Propagate & Close**
18. 🔍 **Propagation: build manifest** — scan conversation for new info
19. **Propagate** — parallel agents if items exist
20. **Wrap-up** — confirm everything done

## Process

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill uses integrations: **slack, clickup, calendar** (plus always-on vault and references).

- Resolve all `{{...}}` tokens from the config "Integration IDs" table.
- Toggle `false` → skip that integration's calls; `true` → test MCP, skip-with-warning if unavailable.
- Never stop the prep for a missing integration. Vault data (team profiles, last weekly record, project status) always drives a usable prep.
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-first.

### Step 1 — calendar check

**(Only if capability `calendar` is configured)** Before asking anything, query the `calendar` MCP:

1. Search for scheduled weekly (today or upcoming days) using `list_events`
2. If found: note date, time, duration, attendees
3. If NOT found: note this — may need to create event later

Present: "Weekly agendada para [dia] às [hora]." or "Não encontrei weekly no calendar."

Se a capability `calendar` não estiver configurada, pergunte ao usuário o horário da reunião em vez de consultar a agenda: "Qual o horário da sua weekly?"

### Step 2 — ⏸️ PAUSE: Ask intention

Before reading any data, use AskUserQuestion:

```
Question 1: "Qual seu foco pra essa weekly?"
Options:
- "Acompanhar entregas" — foco em status, deadlines, accountability
- "Alinhar prioridades" — foco em reprioritização, decisões pendentes
- "Comunicar algo" — anúncio, mudança, feedback coletivo
- "Check-in geral" — sem tema específico, vou direcionar pelos dados

Question 2: "Tem algo que quer comunicar ou decidir nessa weekly?"
→ Plain text (open-ended)
```

**Wait for the owner's response before proceeding.**

Se o gestor disser "não sei" or is vague → proceed to data collection, then suggest focus based on data.

### Step 3 — Load context (Core → Dep Analysis → Targeted)

**Phase A — Core (parallel agents):**

Pre-calculate Unix timestamps in main thread:
- `seven_days_ago`: Unix timestamp for 7 days ago

Spawn agents in parallel using the dedicated CoS loader agents (each declares its own MCPs and tools via frontmatter):

**Agent 1 — Core vault** (`subagent_type: cos-vault-loader`):
- Read profiles of ALL team members in `team/*/` — name, role, specialties, current projects, notes
- Read `team/<owner-slug>/<Owner Name>.md` — as prioridades do gestor and management style
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — as competências de gestão do gestor
- Read last 1 weekly record from `weeklys/` (most recent `YYYY-MM-DD weekly.md`)
- Read `context/decisions.md` — filter for last 14 days
- Return: team member states, as áreas de foco do gestor, last weekly action items, recent decisions

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `docs/reference/integrations.md` — task routing rules, IDs, statuses, comms channel IDs
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming
- Return: routing rules, convention rules, channel IDs

**Phase B — Dependency Analysis (main thread):**

Analyze Core results. From member profiles and last weekly record, extract:
- Members with engagement drop flags (compare last weekly engagement scores) → load dev-plans
- Members with action items recurring 3+ times across meetings → load dev-plans
- Members with dev-plan stagnant 2+ months (check dev-plan `last_updated` in profile) → load dev-plans
- Projects mentioned in member notes or recent decisions → load context files
- task projects to query → focus agent scope

**Phase C — Targeted (parallel agents, only if deps have items):**

**Agent 3 — Targeted vault** (`subagent_type: cos-vault-loader`):
- Dev-plans for flagged members (from Phase B)
- Project context files for active projects (from Phase B)
- Additional weekly records if Phase B identified unresolved patterns

**(Only if capability `comms` is configured)** **Agent A — comms** (`subagent_type: cos-mcp-loader`):
Include in prompt: `#time` = `<team channel from comms MCP details>`, `#projetos` = `<projects channel from comms MCP details>`.

Base:
- `read_channel` `<team channel from comms MCP details>` (oldest: `seven_days_ago`)
- `read_channel` `<projects channel from comms MCP details>` (oldest: `seven_days_ago`)
- `search_public` `from:@member "blocked" OR "stuck" OR "problema" OR "help" after:YYYY-MM-DD` — per team member

Targeted:
- If Phase B identified specific project concerns: targeted search
- Thread expansion only for relevant topics
- No DM reads

- Return: classified comms intelligence per member

**(Only if capability `tasks` is configured)** **Agent B — tasks** (`subagent_type: cos-mcp-loader`):
Include in prompt: Space `<workspace id from tasks MCP details>`.
- Active tasks for each team member (overdue, in progress, blocked)
- O gestor's own pending tasks
- If Phase B identified projects: tasks in those specific projects

**(Only if capability `calendar` is configured)** **Agent C — calendar** (`subagent_type: cos-mcp-loader`):
Include in prompt: timezone `<timezone from calendar MCP details>`.
- Upcoming meetings for the team (next 7 days)
- Verify scheduled weekly exists

Consolidate all results before proceeding.

### Step 4 — 🔍 Quality gate: source completeness

After all agents return, verify each source was consulted:

□ All member profiles loaded?
□ o perfil do gestor + dev-plan loaded?
□ Last weekly record loaded?
□ tasks for ALL members consulted?
□ context/decisions.md filtered (14 days)?
□ comms: channel reads completed (#time, #projetos)?
□ comms: blocker search per member completed?
□ calendar: upcoming events checked?
□ Targeted: flagged dev-plans loaded (if applicable)?
□ Targeted: project context files loaded (if applicable)?

If any source failed → retry once. If still unavailable → note in briefing: "⚠️ [source] indisponível."

### Step 5 — Run team dynamics lens

Internal analysis — NOT shown as raw checklist to the owner. Enriches provocations and alerts.

**PER-MEMBER SNAPSHOT:**
For each team member:
- Current projects and status (from the `tasks` MCP + Slack + last weekly)
- Action items from last weekly: delivered? pending? overdue?
- comms activity level: active, quiet, or silent?
- Engagement trend from last 3 weeklys (if available)
- Dev-plan status: stagnant? progressing?

**FOLLOW-THROUGH ANALYSIS:**
- From last weekly: what % of action items were completed?
- Per-member: who delivers consistently vs who doesn't?
- os próprios compromissos do gestor: fulfilled vs unfulfilled?
- Trend vs last 3 weeklys: improving or declining?

**TEAM DYNAMICS:**
- Who's contributing vs who's silent in channels?
- Cross-member collaboration patterns (who helps whom?)
- Bypass requests: anyone contornando o gestor para chegar ao time?
- Potential tensions or friction signals
- Members who didn't contribute in last 2 weeklys

**DECISION FOLLOW-UP:**
- Recent decisions (last 30 days): which have confirmed implementation?
- Which decisions are still in limbo?
- Postponed decisions from previous weeklys

**WILL'S MANAGEMENT PRACTICE:**
- From o dev-plan do gestor: which competency is he working on?
- Can this weekly be an opportunity to practice it?
- Group coaching opportunities

### Step 6 — Build snapshot

Present quick snapshot to the owner — concise, scannable, 15-min-friendly:

**Team Pulse (1-2 lines per member):**

| Member | Pulse | Highlight / Alert |
|--------|-------|-------------------|
- One-line status per member: what they're focused on + how they're doing
- Source: comms activity, ClickUp patterns, engagement signals
- Do NOT list individual tasks — summarize at the level of "focused on Project X, steady" or "quiet via the `comms` MCP, no `tasks` MCP updates"

**Wins & Recognitions:**
- Members who stood out positively this week (specific achievements, not generic)
- This section is NOT optional — morale matters

**Alerts (only if critical):**
- Members with engagement drops or unusual silence
- Cross-cutting patterns (e.g., tasks hygiene across the team)
- Recurring items from last weekly still unresolved (⚠️ RECORRENTE)
- os próprios compromissos não cumpridos do gestor
- Decisions still in limbo after 2+ weeks
- Do NOT include per-project task lists or blocker details — those belong in project weeklies

### Step 7 — Build strategic agenda

Build agenda **incorporating o input do gestor do Step 2**. Target: **15 minutes total.** Each topic should fit in 2-3 minutes.

**Pauta Estratégica (prioritized for 15min):**
1. **Wins & reconhecimento** (~2min) — always open positive. Morale matters
2. **Rodada rápida** (~5min) — each member shares 1-2 sentences on how they're doing and any blocker. The owner asks follow-ups only if critical
3. **Tema estratégico** (~5min) — 1-2 items max that NEED the whole team's visibility: a decision, an announcement, a cross-cutting concern
4. **os tópicos do gestor** (~3min) — from Step 2, if any

**If a topic needs more than 3 minutes → flag it as "precisa de reunião dedicada" instead of expanding the weekly.**

Time estimate per topic MUST be included. Total MUST NOT exceed 15 minutes.

**Provocações** (enriched by team dynamics lens):
- Members who have been quiet in last 2 weeklys: "Considere puxar [nome] na rodada rápida"
- Team dynamics: "[nome] tem estado mais quieto nas últimas reuniões. Algo pra observar"
- Recurring cross-cutting patterns: "tasks hygiene / comunicação / etc. aparece pela Xª vez — tema estratégico?"
- Follow-through score: "Time entregou X% dos items da última weekly. Tendência: [improving/declining]"
- Dev-plan staleness: "[nome] sem progresso em [competência] há X meses — abordar em 1:1"
- a oportunidade de gestão do gestor: "Oportunidade de praticar [competência] com [situação]"
- Cross-dependencies: "[nome A] depende de [nome B] — alinhar na rodada rápida"
- Do NOT include per-project task status, feature blockers, or bypass incidents — those belong in project weeklies and 1:1s respectively

### Step 8 — 🔍 Quality gate: briefing quality

Before presenting, verify:

□ Snapshot includes ALL team members (no one silently excluded)?
□ Team Pulse is concise (1-2 lines per member, not task lists)?
□ do gestor unfulfilled commitments flagged?
□ Agenda fits within 15 minutes (time estimates included)?
□ No topic exceeds 3 minutes (flagged as "needs dedicated time" if so)?
□ Agenda aligned with a intenção declarada from Step 2?
□ Provocations include at least 1 team dynamics insight (follow-through, silence, cross-deps)?
□ Recurring items (3+) flagged with ⚠️ RECORRENTE?
□ Recognitions/wins section present (not skipped)?
□ No per-project task lists or feature-level details included (scope check)?

If any item fails → fix before presenting.

### Step 9 — ⏸️ PAUSE: Present briefing

Present snapshot first, then agenda + provocations. After presenting, use AskUserQuestion:

```
Question 1: "Como ficou a preparação?"
Options:
- "Boa, salvar" — aprovar e salvar prep file
- "Ajustar pauta" — modificar ordem ou prioridade
- "Adicionar tópico" — incluir algo que não apareceu
- "Mudar foco" — repensar o enfoque da weekly

Question 2 (if ⚠️ RECORRENTE items detected):
"Item '[X]' de [owner] aparece pela Xª vez. Como quer abordar?"
Options:
- "Cobrar na weekly" — endereçar publicamente com expectativa
- "Conversa privada" — tratar em 1:1 ao invés de expor na weekly
- "Redefinir" — talvez o item não faça mais sentido
- "Remover" — não é mais relevante
```

Ask as many questions as needed. **Wait for the owner's response before proceeding.**

Qualquer confirmação positiva conta como aprovação → proceed immediately to save.

### Step 10 — Incorporate feedback

- Apply os ajustes do gestor to the briefing
- Se o gestor adicionar tópicos ou contexto → note for propagation gate later
- Se o gestor compartilhar novas prioridades, strategy, or team concerns → note for propagation

### Step 11 — Save prep file

Create weekly folder if it doesn't exist: `weeklys/YYYY-MM-DD/`

Write `YYYY-MM-DD prep weekly.md` with YAML frontmatter:

```markdown
---
type: prep
subtype: weekly
date: YYYY-MM-DD
status: completed
tags:
  - prep/weekly
---

# Preparação Weekly — YYYY-MM-DD

## Snapshot

### Team Pulse
[Table: member, pulse (1-2 lines), highlight/alert]

### Wins & Reconhecimento
[Specific achievements to recognize]

### Alerts
[Engagement drops, recurring patterns, os compromissos pendentes do gestor, decisions in limbo]

## Contexto do Gestor
[o input do gestor do Step 2 — declared intention, topics, announcements]

## Pauta Estratégica
[Prioritized agenda items]

## Provocações
[Team dynamics insights, blind spots, follow-through analysis]

---
**See also:** [[MOC Meetings]]
```

### Step 12 — calendar sync

- If weekly is NOT on calendar: use AskUserQuestion:
  ```
  "Weekly não está no calendar. Criar evento?"
  Options:
  - "Sim, sugerir horário" — query calendars, present options
  - "Sim, criar recorrente" — weekly recurring event
  - "Não, já está combinado" — skip
  ```
  If approved: create event via `create_event` with title, description (agenda highlights), all team members as attendees
- If weekly IS on calendar: offer to update event description with agenda from prep file. Wait for approval.

### Step 13 — Confirm save

Report to the owner:
- "Preparação salva em `weeklys/YYYY-MM-DD/YYYY-MM-DD prep weekly.md`."
- Calendar status: created/updated/skipped
- "Boa weekly! Depois me manda o áudio que eu processo."

### Step 14 — 🔍 Propagation: build manifest

Scan the ENTIRE conversation for distributable information from o input do gestors during Steps 2, 9-10. Look for:

- **Decisions made** — strategy shifts, priority changes, reprioritization
- **People info** — new context about members or others mentioned
- **Project updates** — status changes, new risks
- **as prioridades do gestor** — focus changes, announcements planned
- **Pendings** — things that surfaced as needed but unresolved

**Deduplication:** Skip anything already captured in the prep file itself.

Build manifest with: item description, category, destination file, action (new/update/skip).

**If nothing to propagate** → skip Step 15, go directly to wrap-up.

### Step 15 — Propagate (parallel agents if items exist)

Spawn agents using `cos-vault-loader` (extended with Write/Edit) per category with items:

- **People Agent** (`subagent_type: cos-vault-loader`): Update profiles in `team/` or `people/` with new info
- **Projects Agent** (`subagent_type: cos-vault-loader`): Update project context files with new status/risks
- **Context Agent** (`subagent_type: cos-vault-loader`): Update context/decisions.md, team.md, pendings.md, o perfil do gestor/dev-plan

Only spawn agents for categories with actual work. Main thread verifies results.

### Step 16 — Wrap-up

Report to the owner:
- Prep file saved: path
- calendar: status
- Propagated: list of files updated (if any)
- "Boa weekly! Depois me manda o áudio que eu processo."

## Edge Cases

- **First weekly ever**: No history — build agenda from `context/team.md` and tasks. Suggest: "Como é a primeira, recomendo focar em alinhar expectativas e estabelecer ritmo"
- **Many overdue action items**: Group by owner and priority. "Temos X items vencidos. Recomendo abrir a weekly resolvendo os 3 mais críticos"
- **Team member absent**: Note in agenda and use AskUserQuestion: "Se [nome] não estiver, quer que envie update por escrito depois?"
- **O gestor tem um anúncio importante**: Prioritize in agenda. "Sendo anúncio importante, sugiro abrir com isso antes dos updates operacionais"
- **Very recent weekly** (<5 days): Focus on follow-up of recent items. Lighter briefing — "Algo mudou desde a última weekly?"
- **No comms activity from a member** (unusual silence): Flag in alerts. "Nenhuma atividade de [nome] no Slack nos últimos X dias."
- **All items on track**: Don't force problems. Briefing can be short. Focus on development and forward-looking topics

## Quality Rules

- **Intent first, data second** — NEVER build the full agenda before understanding o que o gestor quer. Present snapshot, ask, then build agenda
- **15-minute discipline** — the agenda MUST fit in 15 minutes. If it doesn't, cut scope. Per-project deep-dives belong in project weeklies, not here
- **Per-member completeness** — every team member MUST appear in the Team Pulse table. No one gets silently excluded
- **Concise pulse, not task lists** — 1-2 lines per member in the snapshot. Summarize at the level of "focused on X, steady" not "completed task A, started task B, blocked on task C"
- **Provocations must provoke** — generic "pergunte como o time está" is worthless. Every provocation must be grounded in data (follow-through rates, Slack silence, dev-plan staleness, recurring items)
- **os compromissos do gestor são sagrados** — os compromissos não cumpridos DEVEM aparecer in the snapshot. No exceptions
- **Recurrence tracking is mandatory** — items appearing 3+ consecutive weeklys get ⚠️ RECORRENTE
- **Recognize wins** — the recognitions section is NOT optional. Morale matters. If someone delivered, highlight it
- **Scope discipline** — NO per-project task lists, NO feature-level status, NO bypass incidents. Those belong in project weeklies and 1:1s respectively. If a topic needs >3min, flag as "needs dedicated time"
- **Save is mandatory** — the workflow is NOT complete until the prep file is written
- **Wikilinks always** — `[[Full Name]]` for people, `[[Project Display Name]]` for projects

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Team composition: `context/team.md`
- Member profiles: `team/<member>/<First Last>.md` for each member
- Last weeklys: most recent `YYYY-MM-DD weekly.md` in `weeklys/`
- o perfil do gestor: `team/<owner-slug>/<Owner Name>.md`
- o dev-plan do gestor: `team/<owner-slug>/<Owner Name> dev-plan.md`
- Decisions: `context/decisions.md`

If the briefing was built but not saved, re-apresentar ao gestor para confirmação before saving.
If the briefing was saved, proceed to propagation and wrap-up.
