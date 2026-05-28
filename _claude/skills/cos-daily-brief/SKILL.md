---
name: cos-daily-brief
description: Inicia briefing executivo e planejamento colaborativo do dia
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

## Brand Voice

Esta skill conversa diretamente com o gestor. O tom da conversa precisa ser compatível com o estilo dele.

**Antes de gerar qualquer texto, consultar `context/will-brand-voice.md`.**

3 regras-chave para esta skill especificamente:
1. **Pronome**: "a gente" / "você" singular. Nunca "nós" / "vocês".
2. **Sem cushioning**: priorizações e flags são diretas ("X é o primeiro alvo do dia") — não cushioned ("talvez seja interessante olhar para...").
3. **Anti-platitude reflex**: ao motivar/encorajar, use dado/contra-case/declarativa afiada, nunca platitude motivacional. Ver §13 do voice file.

---

Iniciar briefing executivo e planejamento colaborativo do dia.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

IMPORTANT: This is a conversation, not a report. Each phase has a PAUSE where you MUST wait for the owner's input before proceeding.

CRITICAL: Create ONE task per checklist item. Do NOT bundle multiple items into a single task. Each numbered item below = exactly 1 TaskCreate call. Dynamic sub-tasks (e.g., one per task to create, one per calendar event) are created in addition to the checklist tasks.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped.

**Pre-flight**
0. **Load config + capability availability** — read `context/cos-config.md`, enable/skip capability roles per config

**Phase 1 — Collect**
1. **Load context: all sources in parallel** — vault (profiles headers only, Mon: full), references, plus per configured capability: comms (2-layer base + DMs always), tasks, calendar, email
2. **Fetch Claude Code RSS** — main thread (after agents return)

**Phase 2 — Analyze**
3. **Compile executive briefing** — consolidate all sources into presentation sections
4. **Detect celebrations** — identify birthdays/new hires from comms data (e.g. the company channel)
5. **Monday: Run Team Health Lens** — engagement trends, patterns, accountability (skip non-Monday)
6. 🔍 **Quality gate: Briefing Completeness** — verify all sources queried and data comprehensive

**Phase 3 — Brief & Act**
7. **Send celebration messages** — auto-reply in the relevant company channel thread via the `comms` MCP (if detected, with dedup check)
8. **Present executive briefing** — formatted sections, omit empties, mention celebrations sent
9. ⏸️ **PAUSE 1** — AskUserQuestion: briefing review + direction

**Phase 4 — Prioritize**
10. **Suggest prioritized demands** — 3-5 items with justification (🔴🟡🟢)
11. **Dialogue loop** — challenges, proactive scheduling, bypass flags, accountability
12. **Confirm demands** — task references + time estimates
13. ⏸️ **PAUSE 2** — AskUserQuestion: demand table confirmation

**Phase 5 — Plan & Execute**
14. **Create tasks via `tasks` MCP** — one sub-task per new task (per routing rules); if no tasks MCP, create as Obsidian Tasks checkboxes in the project note
15. **Propose time blocks** — based on free time + priorities
16. 🔍 **Quality gate: Plan Feasibility** — hours check, conflicts
17. ⏸️ **PAUSE 3** — AskUserQuestion: time blocks confirmation
18. **Create calendar events** — one sub-task per approved event

**Phase 6 — Propagate**
19. 🔍 **Propagation: build manifest** — scan all info from briefing + the owner's inputs
20. **Propagate: people** — create/update profiles (spawn agent if items exist)
21. **Propagate: projects** — create/update context files (spawn agent if items exist)
22. **Propagate: context files** — decisions, team, company, pendings, skills (spawn agent if items exist)

**Phase 7 — Close**
23. **Save daily brief artifact** — write to `daily-briefs/YYYY-MM-DD.md`
24. **Wrap-up** — report everything saved, created, propagated

## Process

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill can enrich from capability roles: **tasks, comms, calendar, email** (plus the always-on vault and references loaders). Each role maps to one of the user's MCPs in cos-config.md, or is empty (vault-only).

- For each capability role this skill uses, read the matching "MCP details" block from `cos-config.md` and pass them to `cos-mcp-loader` (alongside the role name and `mcp`).
- For each of tasks/comms/calendar/email: if `capabilities.<role>.enabled` is `false` (or no `mcp` set), SKIP that agent in Step 1; otherwise test its MCP and skip-with-warning if unavailable.
- Never stop the brief for a missing capability — the vault + references agents always run, and the brief degrades to what vault data supports.
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-first with all capabilities treated as off.

### Step 1 — Load context (single-wave parallel)

**CRITICAL — Pre-calculate comms timestamps before spawning agents:**

The `read_channel` from the comms MCP tool requires Unix epoch timestamps (seconds). Subagents MUST NOT calculate these themselves — they consistently get the year wrong.

**Before spawning ANY agent**, the main thread MUST:
1. Run Bash to calculate the correct Unix timestamps:
   - `python -c "from datetime import datetime, timedelta; t = datetime.now() - timedelta(days=3); print(int(t.timestamp()))"` (use `python3` if `python` not available)
   - Monday variant: replace `days=3` with `days=7`
2. Pass the **pre-calculated numeric timestamp** to the comms agent prompt as a literal value (e.g., `oldest: 1773716400`)
3. NEVER pass relative descriptions like "3 days ago" — always pass the computed number

Spawn ALL agents in parallel using the dedicated CoS loader agents (each declares its own MCPs and tools via frontmatter):

**Agent 1 — Vault files** (`subagent_type: cos-vault-loader`):
- Read `team/<owner-slug>/<Owner Name>.md` — the owner's priorities
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — the owner's management competencies
- Read all team member profiles from `team/*/` — **frontmatter + first section only** (name, role, current projects). Do NOT read full profile text
- Read `context/pendings.md` — unchecked items
- Read `context/decisions.md` — last 7 days of decisions
- Read most recent `daily-briefs/*.md` — for RSS deduplication + Monday accountability
- Open Obsidian Tasks: scan `- [ ]` lines with a `📅 YYYY-MM-DD` due date across `projects/`, `context/pendings.md`, and recent `daily-briefs/`. Return overdue / due-today / next-3-days (see `docs/reference/obsidian-tasks.md`)
- **Monday extra:** Read full member profiles (not just headers). Read last 2 meeting records per member. Read all daily briefs from the previous week (Mon-Fri) for accountability comparison
- Return: the owner's state, team state summary, pendings, recent decisions, last brief data, open vault tasks (overdue/today/next-3-days), Monday: engagement history + weekly briefs

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `templates/daily-brief.md` — record structure
- Read `docs/reference/integrations.md` — capability roles, MCP-wiring patterns, routing guidance
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming
- Read `memory/reference_claude_code_rss.md` — RSS URL
- Return: template structure, routing rules, convention rules, RSS URL

**(Only if capability `comms` is configured)** **Agent — comms** (`subagent_type: cos-mcp-loader`):
Pass to the loader: role=`comms`, plus the `mcp` name and the "comms" MCP details from cos-config.md.

Base (always):
- Read the primary team channel (oldest: `<pre-calculated timestamp>`, **Monday: 7-day timestamp**) — use the relevant channels from the `comms` MCP details in config
- Read the projects channel (oldest: `<pre-calculated timestamp>`, **Monday: 7-day timestamp**) — use the relevant channels from the `comms` MCP details in config
- **DM with each team member:** cada membro do time (oldest: `<pre-calculated timestamp>`) — **always reads DMs**
- Search per team member: `from:@member "blocked" OR "stuck" OR "problema" OR "help" after:YYYY-MM-DD` — blocker signals; use your handle from the `comms` MCP details in config

Monday expansion:
- Read the company-wide channel (oldest: 7-day timestamp) — use the relevant channels from the `comms` MCP details in config — celebration detection
- Thread expansion for messages with `reply_count > 0` from substantive conversations
- Celebration Detection from company channel: identify birthday/new hire posts (RH), extract person name, type, thread_ts, check if the owner replied

*DM Intelligence — extract and classify:*
- Messages the owner sent that got no reply within 24h → "Mensagens sem resposta (owner → time)"
- Messages received by the owner that he didn't reply to within 24h → "Mensagens sem resposta (time → owner)"
- Messages from anyone outside the team asking team members directly for work → "Bypass Detection"

Return: classified comms intelligence (highlights per channel, DM intelligence, bypass detection, Monday: celebration posts with dedup status)

> Task source: if capability `tasks` is configured, tasks agent leads and the vault tasks from Agent 1 supplement. If not configured, the vault tasks are the task list.

**(Only if capability `tasks` is configured)** **Agent — tasks** (`subagent_type: cos-mcp-loader`):
Pass to the loader: role=`tasks`, plus the `mcp` name and the "tasks" MCP details from cos-config.md.
- The owner's overdue tasks (overdue status) — use the workspace/list IDs from the `tasks` MCP details in config
- The owner's upcoming tasks (next 3 days)
- Solicitações pendentes (inbound requests from other teams)
- Team member tasks with blockers
- **IMPORTANT — Solicitações filter:** Status "solução proposta" = completed. These are NOT active/overdue. Filter them OUT alongside "concluído", "cancelado", and "arquivado". Only show solicitações in "pendente" or "em andamento" as active items.
- Return: tasks snapshot (overdue, upcoming, solicitações, team blockers)

**(Only if capability `calendar` is configured)** **Agent — calendar** (`subagent_type: cos-mcp-loader`):
Pass to the loader: role=`calendar`, plus the `mcp` name and the "calendar" MCP details from cos-config.md.
- List events today + next 3 days — use the timezone from the `calendar` MCP details in config
- Identify conflicts (overlapping events), back-to-back without breaks
- Return: calendar events + conflicts + available slots summary

**(Only if capability `email` is configured)** **Agent — email** (`subagent_type: cos-mcp-loader`):
Pass to the loader: role=`email`, plus the `mcp` name and the "email" MCP details from cos-config.md.
- Search messages últimas 48h — emails importantes, billing, admin, comunicações de stakeholders
- Para emails relevantes: read full content
- Foco: ações pendentes para você, respostas aguardadas, comunicações de parceiros e fornecedores, notificações financeiras
- Return: emails relevantes classificados (ação necessária / informativo / aguardando resposta)

### Step 2 — Fetch Claude Code RSS

Main thread, after agents return. Lightweight — no agent needed.

- WebFetch the Claude Code RSS feed (URL from references)
- Apply deduplication: extract versions already covered in the most recent daily brief(s)
- Only keep versions newer than the last covered version
- If no previous brief has this section, keep the 2 most recent versions only
- For each new version, classify CoS impact:
  - **Relevante pro CoS:** Features that directly benefit this vault, workflows, or the owner's daily use
  - **Interessante:** Notable features worth knowing but not directly impactful
  - Skip bug fixes and minor changes unless they fix something you have encountered

Consolidate all agent results + RSS before proceeding to Step 3.

### Step 3 — Compile executive briefing

Consolidate all agent results into the briefing. Sections (omit any section with no items):

1. **Greeting** + date + day of week (ALWAYS verify day-of-week via calendar calculation)
2. **Tarefas urgentes** — overdue tasks with days overdue (from the `tasks` MCP). **DEDUP RULE:** Do NOT include tasks from the Solicitações list here — those appear ONLY in section 4
3. **Tarefas próximas** — upcoming tasks next 3 days with deadlines (from the `tasks` MCP)
4. **Solicitações pendentes** — inbound requests from other teams (from the `tasks` MCP)
5. **Slack highlights** — key discussions, blockers, help requests, notable activity (from the `comms` MCP L1-L3)
6. **comms intelligence** — unanswered messages (both directions), bypass detection (from comms DM analysis)
7. **Celebrações detectadas** — birthdays/new hires found, dedup status (from the `comms` MCP celebration data)
8. **Agenda do dia** — today's meetings with times + next 3 days (from the `calendar` MCP)
9. **Conflitos de calendar** — overlapping events, back-to-back without breaks (from the `calendar` MCP)
10. **Emails relevantes** — actions needed, responses awaited, partner communications (from email)
11. **Risk alerts** — stale context files (>30 days), missing 1:1s (>35 days), recurring blockers (from vault)
12. **Pendings** — unchecked items from `context/pendings.md`
13. **Claude Code updates** — new versions since last brief with CoS impact analysis (from RSS)

**Proactive scheduling injection:** If any team member's last 1:1 was >35 days ago AND there's a free slot today → note for demand suggestion in Step 15 ("Faz X dias sem 1:1 com [nome]. Slot livre às [hora]. Quer agendar?")

### Step 4 — Detect celebrations

From the comms agent's celebration data:

1. Filter for posts where the owner has NOT already replied (dedup check from Step 3)
2. For each unreplied celebration:
   - Classify: `birthday` or `new_hire`
   - Extract: person name, original post timestamp (`thread_ts`), channel ID
3. If celebrations found → prepare for auto-send in Step 12
4. If none found → mark step as completed, Step 12 will be a no-op

### Step 5 — Monday: Run Team Health Lens

**SKIP on non-Monday days.** Mark as completed with note "Not Monday — skipped."

**ENGAGEMENT TRENDS:**
- For each team member, pull engagement scores (Mood, Motivation, Workload, Satisfaction) from the last 2 meeting records
- Calculate trajectory: ↑ improving, → stable, ↓ declining
- Flag any dimension that dropped ≥2 points

**PATTERNS CROSS-MEETING:**
- Action items pending for 2+ weeks across members
- Recurring themes that appeared in multiple meetings
- Blockers that persisted through the week

**WEEKLY ACCOUNTABILITY:**
- Read all daily briefs from the previous week
- For each day: count demands planned vs demands that actually got completed (based on `tasks` MCP status or next day's brief mentioning completion)
- Calculate execution rate per day and weekly total
- If rate <60%: flag "Taxa de execução da semana passada: X%. Planejamento precisa de ajuste?"

### Step 6 — 🔍 Quality gate: Briefing Completeness

Before presenting, verify each item explicitly:

□ All sources queried or degradation noted? (tasks, comms, calendar, email capabilities, RSS, local files)
□ **comms data year validation?** — Verify that ALL comms messages, threads, and celebration posts are from the CURRENT YEAR. If any message timestamps resolve to a different year, STOP and re-query with corrected timestamps. This is a **hard gate** — do NOT proceed with stale-year data.
□ Deduplication RSS applied? (no versions already covered in previous briefs)
□ calendar conflicts identified? (overlapping events, back-to-back)
□ comms DM intelligence extracted? (unanswered both directions, bypass)
□ Celebration detection completed? (birthday/new_hire/none with dedup status)
□ Monday: Team Health Lens completed? (engagement, patterns, accountability)

**Degradation rules** — if any capability source fails, degrade gracefully:
- `tasks` fails → "[tasks indisponível — tarefas não consultadas]"
- `comms` fails → skip comms sections + celebrations with note
- `calendar` fails → skip calendar sections with note
- `email` fails → skip email section with note
- All capability sources fail → present local data only + warn you

If any item fails that can be fixed → fix before presenting. If MCP degradation → note and proceed.

### Step 7 — Send celebration messages

**If no celebrations detected in Step 9 → mark as completed, skip to Step 13.**

For each celebration where the owner hasn't replied yet:

1. **Generate message** — short, informal, varied, in the owner's style:
   - Birthday: ~1-2 sentences, congratulatory, positive. Reference style: "Parabéns [nome]! 🎉 Que venham muitas conquistas"
   - New hire: ~1-2 sentences, welcoming, supportive. Reference style: "Bem-vindo(a) [nome]! Qualquer coisa pode contar comigo 🙏"
   - VARY each message — never send the exact same text twice. Use different wordings, emojis, and structure each time
   - Keep the tone natural and casual, like the owner would write via the `comms` MCP
2. **Send via `send_message`** with `thread_ts` of the original HR post (reply in thread, not new message)
3. **Log** what was sent: person name, type, message text — for the daily brief artifact

**No approval needed** — celebrations are sent automatically. You are informed in the briefing (Step 13).

### Step 8 — Present executive briefing

Present the compiled briefing following the section order from Step 8. Format with markdown tables and bullet points.

If celebrations were sent in Step 12, include a line: "Enviei [parabéns/boas-vindas] pro(a) [nome] no #empresa."

**Monday extra sections** (after Risk Alerts):
- **Team Health: Engagement Trends** — table with member, scores, trajectories
- **Team Health: Padrões Cross-Meeting** — persistent themes, stale action items
- **Team Health: Accountability Semanal** — last week's execution rate table

**Empty state**: If ALL sections are empty: "Nenhuma pendência ou alerta. Dia livre para focar no que quiser."

### Step 9 — ⏸️ PAUSE 1

Use AskUserQuestion:

```
Question 1: "Como ficou o briefing?"
Options:
- "Completo, pode priorizar" — proceed to Phase 4
- "Perdi algo — vou adicionar" — you add context, then re-present or proceed
- "Só o briefing hoje" — STOP here, jump to Step 28 (save artifact) and wrap up
```

If you add context, new priorities, or corrections → incorporate into the data before Phase 4.

If you say "só o briefing" → **STOP**. Save the briefing artifact (jump to Step 28) and wrap up. Do NOT proceed to Phase 4.

**WAIT.** Do NOT proceed until you respond.

### Step 10 — Suggest prioritized demands

Based on briefing data + the owner's input from PAUSE 1:

Suggest 3-5 prioritized demands using markers:
- 🔴 **Urgent/overdue** — immediate action needed (overdue tasks, critical blockers)
- 🟡 **Important/upcoming** — due soon or high impact (approaching deadlines, proactive scheduling)
- 🟢 **Proactive** — not urgent but valuable (development, strategy, context maintenance)

Each demand includes: task name + reason for priority ranking + estimated time (if inferable).

**Proactive scheduling** (from Step 8): If any team member's 1:1 is overdue >35 days AND a free slot exists today, include as 🟡 demand: "Preparar e agendar 1:1 com [nome] — faz X dias."

### Step 11 — Dialogue loop

You may approve, remove, add, or reorder items. This is a dialogue — go back and forth until agreement.

**CoS challenges proactively:**
- "Você mencionou X mas não incluiu — tem certeza que não é prioridade?"
- "Essa task está vencida há X dias. Quer incluir hoje ou remarcar?"
- "Vi bypass no comms: [pessoa] pediu diretamente ao [membro]. Quer abordar isso hoje?"

**Schedule accountability (from memory):** Be aggressive about the owner's schedule. If they're deferring important items repeatedly, call it out: "Essa é a Xª vez que isso é adiado. Quer resolver hoje ou tirar da pauta?"

### Step 12 — Confirm demands

For each agreed demand:
- **Already has task?** → Reference it (ID + name + current status)
- **No task?** → "Vou criar task em [lista, per routing rules]. Assignee: você. Deadline: hoje."
- **Estimated time?** → "Quanto tempo quer reservar pra isso?"

### Step 13 — ⏸️ PAUSE 2

Present the final demand table:

| # | Prioridade | Demanda | Tempo estimado | ClickUp |
|---|-----------|---------|----------------|---------|

Use AskUserQuestion:

```
Question 1: "Essas são as demandas do dia. Confirma?"
Options:
- "Confirmado" — proceed to Phase 5
- "Preciso ajustar" — you modify, then re-present table
- "Adicionar demanda" — you add new items
```

If you defer items → capture in "Adiamentos" for the artifact. If you add items → add to the table.

**Pendings capture:** If you defer a decision or leave something unresolved, add to `context/pendings.md`.

**WAIT.** Do NOT proceed until you respond.

### Step 14 — Create tasks

For each demand that doesn't have a task, create a **dynamic sub-task** and execute:
- Follow routing rules from `docs/reference/integrations.md`
- Assignee: você (your user id from the `tasks` MCP details)
- Deadline: today
- Description: `Source: Daily brief YYYY-MM-DD`
- If task already exists: update status to `em andamento` if currently `pendente`

### Step 15 — Propose time blocks

1. Query the owner's free time via the `calendar` MCP (using `cos-mcp-loader` with role=`calendar`)
2. For each demand, suggest a time block:
   - **Event title:** `🎯 [Task Name]`
   - **Description:** task reference + brief context
   - **No attendees** (personal focus blocks)
   - **calendar:** the owner's primary calendar
   - **Timezone:** the timezone from the `calendar` MCP details

**Time block rules:**
- Respect existing meetings — never overlap
- 15min buffer between blocks
- No blocks before 8h or after 18h (unless you explicitly ask)
- Morning preference for deep work, afternoon for meetings/communication

### Step 16 — 🔍 Quality gate: Plan Feasibility

Check and report:

□ Total estimated hours ≤ available free hours?
□ No time blocks before 8h or after 18h?
□ If day has >6h of meetings: alert "Dia com Xh de reunião — Yh restante pra foco"

If hours don't fit → suggest which demands to defer or whether to extend the work window. Present the conflict, don't silently adjust.

**Fully booked calendar:** If no free slots available:
1. Which meetings could potentially be shortened
2. Whether to extend the work window (earlier/later)
3. Whether to defer lower-priority demands to tomorrow

### Step 17 — ⏸️ PAUSE 3

Present the proposed time blocks:

| # | Demanda | Horário | Duração |
|---|---------|---------|---------|

Include feasibility summary: "Dia com Xh de reunião e Yh disponível. Cabem as Z demandas de Wh total."

Use AskUserQuestion:

```
Question 1: "Vou criar esses time blocks e as tasks pendentes. Confirma?"
Options:
- "Confirma tudo" — create all time blocks and tasks
- "Ajustar horários" — you modify time blocks
- "Sem time blocks hoje" — skip calendar events, only create tasks
```

**WAIT.** Do NOT proceed until you respond.

### Step 18 — Create calendar events

**If you chose "Sem time blocks" → mark as completed, skip.**

For each approved time block, create a **dynamic sub-task** and execute:
- `create_event` with the parameters from Step 20
- Confirm each creation: "Bloco criado: [nome] às [hora]"

### Step 19 — 🔍 Propagation: build manifest

Scan ALL information consumed during this workflow — from data collection AND from the owner's inputs during PAUSEs 1-3 — and build the propagation manifest.

**Deduplication rule:** Avoid duplicating what was already written during Steps 19-23. Focus especially on the owner's reactions, decisions, strategy shifts, and new context shared during the interactive phases.

**PEOPLE:**
□ New person mentioned? → Create profile using `templates/person.md`
□ Existing person — new info? → Update profile notes
□ Need IDs? → `search_users` / `find_member_by_name`

**PROJECTS:**
□ New project mentioned? → Create context using `templates/project-context.md`
□ Existing project — status/risk/decision changed? → Update context file

**DECISIONS:**
□ Any decision made during prioritization or planning? → Append to `context/decisions.md` with Tipo (estrutural/operacional)

**TASKS:**
□ All tasks created/updated correctly? (verify count matches demands)
□ Existing tasks impacted by decisions? → Update status/assignee/deadline

**SKILLS & DEVELOPMENT:**
□ Competency discussed or demonstrated? → Update member profile `skills:` frontmatter
□ Owner practiced management competency? → Log to `Owner Name dev-plan.md` Situation Log

**CONTEXT FILES:**
□ Team composition changed? → `context/team.md`
□ Company info changed? → `context/company.md`
□ Something Claude needs from you? → Append to `context/pendings.md`

Each sub-item: if applies → execute. If not → skip explicitly.

### Steps 25-27 — Parallel propagation agents

Spawn agents using `cos-vault-loader` (extended with Write/Edit) only for categories with actual work. Skip categories with nothing to propagate.

**Step 25 — People Agent** (`subagent_type: cos-vault-loader`) (if people items exist):
- Create/update profiles in `team/` and `people/`
- Lookup Slack/tasks MCP IDs via MCP
- For external people/companies: use WebSearch to enrich profiles

**Step 26 — Projects Agent** (`subagent_type: cos-vault-loader`) (if project items exist):
- Create/update project context files in `projects/`
- For projects involving external tools: use WebSearch for context

**Step 27 — Context Agent** (`subagent_type: cos-vault-loader`) (if context items exist):
- Update `context/decisions.md`, `context/team.md`, `context/company.md`, `context/pendings.md`
- Update `team/<owner-slug>/<Owner Name> dev-plan.md` if applicable
- Update member profile `skills:` frontmatter if applicable

Main thread verifies all agent results before marking propagation gate as completed.

### Step 23 — Save daily brief artifact

Save to `daily-briefs/YYYY-MM-DD.md` using `templates/daily-brief.md`.

**Rules:**
- Fill all sections that have data
- **Remove empty sections** from the final file (don't leave placeholder rows)
- Monday: include Team Health section (engagement, patterns, accountability)
- Non-Monday: remove Team Health section entirely
- Include comms intelligence section only if items exist
- Include Celebrações section only if celebrations were sent
- Include Claude Code Updates only if new versions since last brief
- YAML frontmatter: `type: daily-brief`, `date: YYYY-MM-DD`, `tags: [daily-brief]`

**Sections to fill:**
- **Briefing Summary:** one-line-per-bullet highlights from Phase 2
- **Tarefas tasks:** snapshot of the owner's active/overdue tasks at time of briefing
- **Solicitações:** inbound requests from other teams
- **comms Highlights:** notable activity from team/company channels
- **comms intelligence:** unanswered messages, bypass detection
- **Celebrações:** birthdays/welcomes detected and messages sent
- **Agenda:** today's events + next 3 days
- **Risk Alerts:** stale files, missing 1:1s, recurring blockers
- **Team Health:** (Monday only) engagement trends, patterns, accountability
- **Pendings:** unchecked items from pendings.md
- **Claude Code Updates:** new versions + CoS impact analysis
- **Demandas do Dia:** prioritized table from Phase 4 (with time blocks and task references)
- **Decisões:** decisions made during prioritization
- **Adiamentos:** items deferred with reason
- **Contextos Atualizados:** vault files modified during this workflow

### Step 24 — Wrap-up

Report to you:
- Daily brief saved: `daily-briefs/YYYY-MM-DD.md`
- Celebrations sent: list each with person name and type (or "Nenhuma")
- tasks created/referenced: list each with name and ID
- calendar events created: list each with time (or "Nenhum")
- Decisions appended: list each with # from context/decisions.md (or "Nenhuma")
- Profiles/projects/context updated: list files touched (or "Nenhum")
- Deferred items: list with suggested dates (or "Nenhum")
- Key watch items: 2-3 things to monitor through the day

"Seu dia está organizado. Bom trabalho!"

## Edge Cases

- **Session-start overlap:** If invoked right after session start and briefing data was already presented in this session, reuse existing context — skip Phase 1, go directly to Step 8 with cached data. Only re-query if you explicitly request or significant time has passed.
- **Invoked mid-day (re-planning):** Phase 1 still collects fresh data. Phase 4 focuses on remaining time — "Considerando que já são [hora] e você tem [X]h restantes, sugiro focar em..."
- **No tasks at all:** Skip Phase 4 prioritization, ask you: "Não encontrei tarefas pendentes. Tem algo que quer atacar hoje?"
- **All tasks are team tasks (nothing for you):** Present team status, ask if you want to plan personal focus time (strategy, training, context maintenance).
- **Wants to skip planning:** If you say "Só o briefing hoje" at PAUSE 1 → stop after Phase 3, save artifact with briefing-only content, wrap up.
- **Fully booked calendar:** If no free slots → present options: shorten meetings, extend work window, defer demands.
- **MCP degradation:** If any source fails → degrade gracefully with note, never block the workflow.
- **Celebration already replied:** If the owner already replied in the thread (detected by dedup check) → skip that celebration, log "Já respondido" in artifact.
- **Multiple celebrations same day:** Send each as a separate thread reply. Each message should be unique (varied wording).
- **Celebration post is old (>7 days):** Skip — too late for a timely response. Log "Post antigo, não respondido."

## Quality Rules

- **calendar events**: NEVER create without your explicit approval (PAUSE 3)
- **tasks**: Follow routing rules from `docs/reference/integrations.md` strictly
- **Engagement scores**: Only reference from actual meeting records. NEVER fabricate.
- **comms DM intelligence**: Report factual data (message sent, no reply in X hours). Do NOT interpret emotional state from message patterns.
- **Schedule accountability**: Be aggressive about the owner's schedule (memory: feedback_schedule_accountability). Don't soften — challenge directly when items are repeatedly deferred.
- **Day of week verification**: ALWAYS verify day-of-week before referencing dates. Use calendar calculation. NEVER assume or guess.
- **Celebration messages**: Keep short (max 2 sentences), informal, varied. Never repeat exact same message. Send as thread reply only.
- **Task granularity**: Create ONE task per checklist item. Sub-tasks for ClickUp/Calendar are additional. Never bundle.
- **Obsidian**: All files MUST include YAML frontmatter per `docs/reference/conventions.md`. Use `[[wikilinks]]` for all person/project references.

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Last daily brief: most recent `daily-briefs/YYYY-MM-DD.md`
- Owner profile: `team/<owner-slug>/<Owner Name>.md`
- Owner dev plan: `team/<owner-slug>/<Owner Name> dev-plan.md`
- Pendings: `context/pendings.md`
- Decisions: `context/decisions.md`
- Template: `templates/daily-brief.md`
- Routing rules: `docs/reference/integrations.md`

If data collection completed but briefing not presented, recompile from cached data.
If briefing presented but prioritization not done, present demands directly.
If celebrations detected but not sent, check dedup status again before sending.
