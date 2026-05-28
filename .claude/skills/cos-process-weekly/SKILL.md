---
name: cos-process-weekly
description: Processa transcrição de weekly e conduz debriefing interativo com o gestor
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

Processar transcrição da weekly do time.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

IMPORTANT: Do NOT save the meeting record before debriefing. The conversation with the owner comes first.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped. Create sub-tasks dynamically as needed (e.g., one task per task to create, one per profile to update).

**Pre-flight**
0. **Load config + integration availability** — read `context/cos-config.md`, resolve tokens, toggle integrations

**Phase 1 — Collect**
1. **Transcribe audio** — run transcription script, never ask the owner for text
2. **Dependency Analysis** — analyze transcription, extract entities and coaching signals
3. **Load context: single-wave parallel agents** (Core + Targeted)

**Phase 2 — Analyze**
4. **Draft weekly record** — generate all sections from transcription (do NOT save)
5. **Run Team Dynamics Lens** — internal analysis (follow-through, group dynamics, coaching, cross-dependencies)

**Phase 3 — Debrief**
6. ⏸️ **PAUSE: Block A** — "O que capturei" + "Dinâmicas que observei" + validation
7. ⏸️ **PAUSE: Block B** — "Minha leitura" + "Cross-impact e follow-ups"
8. **Incorporate feedback** — adjust draft with the owner's corrections

**Phase 4 — Quality Check**
9. 🔍 **Quality gate: Record Quality** — structure + content completeness
10. 🔍 **Quality gate: Accountability Quality** — follow-through, recurrence, score

**Phase 5 — Save & Execute** (one task per discrete action — create sub-tasks dynamically for multi-item steps)
11. **Save weekly record** — write to `weeklys/YYYY-MM-DD/` with full frontmatter per conventions.md
12. **Update member profiles** — one sub-task per member with updates: edit `team/<member>/<Name>.md` with notes and observations for upcoming 1:1s
13. **Create tasks** — one sub-task per action item extracted (`create_task` per item, route per integrations.md)
14. **Append decisions** — one entry per decision to `context/decisions.md` with sequential #, Tipo (estrutural/operacional), Source Meeting wikilink
15. **Update owner's dev-plan** — conditional: add to Situation Log in `team/<owner-slug>/<Owner Name> dev-plan.md` if the owner practiced a management competency
16. **Update skills-matrix** — conditional: update member profile frontmatter (`skills:` YAML block) if competencies discussed
17. **Send comms canvas + DMs** — create Canvas with full weekly record adapted for Slack, then DM each member with Canvas link + short summary of their action items
18. ⏸️ **Check next weekly** — query calendar via `list_events`, suggest scheduling if not found

**Phase 6 — Propagate** (one sub-task per category with items — spawn Sonnet agents in parallel if 2+ categories)
19. 🔍 **Propagation: build manifest** — scan session for new/updated people, projects, context; classify by category
20. **Propagate: people** — conditional: create/update profiles in `people/` using `templates/person.md` (spawn agent if items exist)
21. **Propagate: projects** — conditional: create/update context files in `projects/<slug>/` using `templates/project-context.md` (spawn agent if items exist)
22. **Propagate: context files** — conditional: update `context/team.md`, `context/company.md`, `context/pendings.md`, `team/skills-matrix.md` (spawn agent if items exist)

**Phase 7 — Close**
23. **Wrap-up** — report to you: files saved, tasks created, decisions logged, profiles updated, Slack sent, next steps

## Process

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill uses integrations: **slack, clickup** (plus always-on vault and references).

- Resolve all `{{...}}` tokens from the config "Integration IDs" table.
- Toggle `false` → skip; `true` → test MCP, skip-with-warning if unavailable.
- Never stop processing for a missing integration. The transcription + vault context always produce the meeting record; integrations only enrich (task creation, Slack cross-reference).
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-first.

### Step 1 — Transcribe audio

**You MUST run the transcription script before doing ANYTHING else.** Do NOT ask the owner for the transcription text. Do NOT skip this step.

1. Find the audio file: search for `Recording*.m4a` (or .mp3/.wav) in the vault root, or ask for the path
2. **RUN**: `python scripts/transcrever_audio.py "<audio_file>" --type weekly [--date YYYY-MM-DD]`
   - Script auto-creates meeting folder, moves audio, converts to WAV, transcribes via Whisper
   - Wait for it to complete (may take 1-3 min depending on audio length)
   - Only skip if `transcription.txt` ALREADY EXISTS in `weeklys/YYYY-MM-DD/`
3. Read transcription from `weeklys/YYYY-MM-DD/transcription.txt`

**If transcription fails:** Report the error. Offer: "Quer me contar o resumo da reunião por texto? Consigo montar o registro a partir disso."

### Step 2 — Dependency Analysis (main thread)

Analyze the transcription and extract a structured dependency list. This runs in the main thread (~5 seconds), no subagent.

**Extract:**
- **people**: Names mentioned beyond the team. Check against `team/` and `people/` folders
- **projects**: Project names referenced (match against `projects/` folder names)
- **coaching_signals**: Members who received feedback, coaching, or had development discussed (for targeted dev-plan loading)
- **decisions_keywords**: Keywords to filter `context/decisions.md` (beyond the last 14 days filter)
- **external_entities**: Companies, tools, partners not documented in the vault
- **slack_topics**: Specific keywords for targeted comms searches (beyond base blocker search)
- **needs_history**: `true` if transcription references prior weeklys ("da última vez", "a gente combinou", "como ficou aquilo")

**Output format** (internal, not shown to user):

```
deps = {
  people: [],
  projects: [],
  coaching_signals: [],
  decisions_keywords: [],
  external_entities: [],
  slack_topics: [],
  needs_history: false
}
```

This output feeds the Targeted portions of Step 3 agents.

### Step 3 — Load context (single-wave parallel)

Pre-calculate Unix timestamps in main thread before spawning agents:
- `seven_days_ago`: Unix timestamp for 7 days ago

Spawn ALL agents in parallel using dedicated CoS loader agents (each declares its own MCPs and tools via frontmatter):

**Agent 1 — Core vault** (`subagent_type: cos-vault-loader`):
- Read profiles of ALL team members in `team/*/` — name, role, specialties, current projects, notes
- Read `team/<owner-slug>/<Owner Name>.md` — owner's priorities and management style
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — owner's management competencies
- Read last 1 weekly record from `weeklys/` (most recent `YYYY-MM-DD weekly.md`)
- Read `context/decisions.md` — filter for decisions from last 14 days
- Return: team member states, owner's focus areas, last weekly action items, recent decisions

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `templates/weekly.md` — record structure
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming
- Return: template structure, convention rules
- Note: `integrations.md` is NOT read here — static IDs are embedded in agent prompts. Full `integrations.md` read at Phase 5.

**Agent 3 — Targeted vault** (`subagent_type: cos-vault-loader`) (only if deps have items):
- If `deps.coaching_signals` has names: read their dev-plans from `team/<member>/<Name> dev-plan.md`
- If `deps.projects` has names: read their context files from `projects/<name>/<Name>.md`
- If `deps.needs_history`: read weekly records #2 and #3 from `weeklys/`
- If nothing to load: skip this agent entirely
- Return: dev-plans of discussed members, project context, historical weekly data

**(Only if capability `comms` is configured)** **Agent A — comms** (`subagent_type: cos-mcp-loader`):
Include in prompt: `#time` = `<team channel from comms MCP details>`, `#projetos` = `<projects channel from comms MCP details>`.

Base (always):
- `read_channel` `<team channel from comms MCP details>` (oldest: `seven_days_ago`)
- `read_channel` `<projects channel from comms MCP details>` (oldest: `seven_days_ago`)
- `search_public` `from:@member "blocked" OR "stuck" OR "problema" OR "help" after:YYYY-MM-DD` — for each member discussed in transcription

Targeted (from deps):
- If `deps.slack_topics` has items: targeted searches
- For messages with `reply_count > 0` that match targeted topics: `read_thread`

- Return: classified comms intelligence per member

**(Only if capability `tasks` is configured)** **Agent B — tasks** (`subagent_type: cos-mcp-loader`):
Include in prompt: Space `<workspace id from tasks MCP details>`.
- Active tasks for each team member (overdue, in progress, blocked)
- If `deps.projects` has names: tasks in those specific projects
- Return: tasks snapshot with status, blockers, overdue items per member

**Agent C — calendar** (`subagent_type: cos-mcp-loader`):
Include in prompt: timezone `<timezone from calendar MCP details>`.
- Upcoming meetings for the team (next 14 days)
- Return: scheduled meetings, potential conflicts

**WebSearch (main thread, after agents return):**
- If `deps.external_entities` has items: search for context

Consolidate all agent results before proceeding to Step 4.

### Step 4 — Draft weekly record + Team Dynamics Lens

**3A. Generate the weekly record draft internally (do NOT save yet).**

Follow `templates/weekly.md` structure. Extract from transcription:
- Previous Action Items Review with real status per item (cross-reference with last weekly)
- Recurrence flags: if item appeared in 3+ consecutive weeklys → ⚠️ RECORRENTE
- Follow-through Score: X concluded / Y total (Z%)
- Team Member Updates for every participant
- Project Progress with status per project (On Track / At Risk / Blocked)
- Blockers & Escalations
- Decisions Made with rationale and impact
- Announcements
- Discussion Notes
- Coaching Moments (classify each: Coaching / Directing / Solving)
- Team Dynamics (participant role: Led / Active / Passive / Absent)
- Action Items with owners (ask for deadlines if not mentioned)
- Key Takeaways
- Next Weekly

**3B. Run Team Dynamics Lens internally.**

This analysis runs silently. Its output feeds into Blocks 2-4 of the debriefing. NOT presented as a raw checklist to the owner.

**DIMENSION 1 — Follow-through Coletivo:**
- % of action items from last weekly concluded (per member and total)
- Who consistently delivers vs who doesn't — identify patterns across last 3 weeklys
- Items ⚠️ RECORRENTE: how many meetings without resolution, who owns them
- Owner's own commitments from last weekly: fulfilled or not?
- Follow-through trend: improving, stable, or worsening vs last 3 weeklys

**DIMENSION 2 — Dinâmica de Grupo:**
- Who led discussions (approximate % of talk time, who set the agenda)
- Who stayed silent or passive
- Tensions or misalignments between members
- Collaboration patterns: who helped whom, who offered support
- Absent members: who was missing, potential impact
- Positive dynamics worth recognizing

**DIMENSION 3 — Coaching em Grupo:**
- When member brought a challenge: did the owner coach (asked questions), direct (told what to do), or solve (did it themselves)?
- Moments where the owner could have asked instead of answered
- Moments of delegation vs centralization
- Leadership natural emergente: did any member take ownership of a discussion topic?
- If notable: link to owner's dev-plan competency being practiced or missed

**DIMENSION 4 — Cross-dependencies:**
- Decisions that impact more than one member or project
- Workload overlap: member appearing in multiple projects — load ok?
- Timeline dependencies between projects
- Shared resources at risk
- Commitments that are vague ("vai ver", "tenta") vs concrete (owner + deadline)

### Step 5 — ⏸️ PAUSE: Debriefing Block A

Present "O que capturei" + "Dinâmicas que observei" together:

**"O que eu capturei":**
- Executive summary (5-7 lines): main topics, decisions, commitments
- Follow-through Score: "Da weekly passada, X de Y items concluídos (Z%)"
- Action items por membro with deadlines
- Decisions extracted with rationale
- Validation: "Confirmei que [nome] ficou com [X] até [data]. Correto?"

**"Dinâmicas que observei":**
- Who contributed actively vs who stayed quiet
- Tensions or misalignments observed
- Quotes that reveal dynamics: "[nome] disse '[quote]' — algo a observar?"
- Missing participation: "[nome] não falou sobre [projeto]. Tudo certo?"
- Positive dynamics: "[nome] ajudou [nome] com [tema] — bom sinal de colaboração"
- Absent members and potential impact
- Leadership natural: "[nome] assumiu a discussão sobre [tema]"

**Use AskUserQuestion for structured validation:**

```
Question 1: "Como ficou a captura + dinâmicas?"
Options: "Bate, pode avançar" / "Preciso corrigir fatos" / "Quero adicionar contexto" / "Refazer"

Question 2 (per action item without deadline):
"Deadline para '[action item]' do [nome]?"
Options: "Esta semana" / "Próxima semana" / "Sem prazo" / "Definir data"

Question 3 (if ⚠️ RECORRENTE items detected, one per item):
"Item '[X]' do [nome] aparece pela Xª vez sem resolução. Ação?"
Options: "Escalar" / "Cobrar diretamente" / "Delegar" / "Remover da pauta"
```

**WAIT.** Do NOT proceed until you respond.

### Step 6 — ⏸️ PAUSE: Debriefing Block B

Present "Minha leitura" + "Cross-impact e follow-ups" together:

**"Minha leitura":**
- Follow-through coletivo: trend (improving/worsening/stable) with evidence
- Accountability per member: "[nome] entregou X/Y, [nome] entregou X/Y"
- Coaching moments summary: "Identifiquei X momentos coaching, Y directing, Z solving"
- Owner's blind spots: "Você não perguntou sobre [tema pendente]"
- Manager development (only if notable): "Boa facilitação em [situação]. Registrar no dev-plan?"
- Owner's unfulfilled commitments: "Você se comprometeu com [X] na weekly passada. Foi feito?"

**"Cross-impact e follow-ups":**
- Decisions impacting workload of other members
- Dependencies between projects: "[projeto A] depende de [deliverable] do [nome] em [projeto B]"
- Vague commitments: "[nome] disse que vai 'ver' — recomendo pedir ETA concreto"
- Topics for individual 1:1s: "Recomendo abordar [tema] com [nome] na próxima 1:1"
- Unresolved items: "Esse tópico ficou sem conclusão. Resolver async ou na próxima weekly?"

**Use AskUserQuestion:**

```
Question 1: "Bate com sua leitura?"
Options: "Sim, pode salvar" / "Preciso corrigir" / "Quero adicionar contexto"

Question 2 (if manager development observation):
"Registrar '[observação]' no seu plano de desenvolvimento?"
Options: "Sim, registrar" / "Não, foi rotina" / "Sim, mas reformular"

Question 3 (if topics suggested for 1:1s):
"Anotar esses temas nas observações dos perfis para próximas 1:1s?"
Options: "Sim, todos" / "Selecionar quais" / "Não anotar"
```

**WAIT.** Do NOT proceed until you respond.

### Step 7 — Incorporate feedback

- Apply the owner's corrections and additions to the draft
- Note any new information shared during debriefing — these feed the propagation gate later
- If the owner confirmed a management development observation → note for dev-plan update
- If the owner added 1:1 topics per member → note for profile updates
- Update Follow-through Score if the owner corrected item statuses

### Step 8 — 🔍 Quality gate: Record Quality

Before saving, verify each item explicitly:

**STRUCTURE:**
□ All template sections filled or explicitly marked as not applicable?
□ YAML frontmatter complete? (type: meeting, subtype: weekly, date, participants, absent, status, tags)
□ All person mentions use `[[Full Name]]` wikilinks?
□ All project references use `[[Project Display Name]]` wikilinks?
□ Navigation footer present? (`See also: [[MOC Meetings]]`)

**CONTENT:**
□ Previous Action Items reviewed with actual status from last weekly? Recurrence flags for 3+?
□ Follow-through Score calculated correctly?
□ Team Member Updates filled for ALL participants present?
□ Every action item has an owner?
□ Project Progress table filled for all active projects discussed?
□ Blockers listed with owner and severity?
□ Coaching Moments table filled with moments from the meeting?
□ Team Dynamics table filled for all participants?
□ Inaudible sections marked with `[inaudível]`?

If any item fails → fix before proceeding. Do NOT mark this step completed with failures.

### Step 9 — 🔍 Quality gate: Accountability Quality

Before saving, verify:

□ ALL action items from the previous weekly were reviewed (no omissions)?
□ Status is real for each item (Done / In Progress / Not Started / Blocked), not generic?
□ Items appearing 3+ consecutive weeklys → ⚠️ RECORRENTE flagged?
□ Follow-through Score calculated? (% concluded / total from previous weekly)
□ Owner's own commitments from last weekly verified?
□ Accountability trend noted? (improving / stable / worsening vs last 3 weeklys)

If any item fails → fix before proceeding.

### Step 9 — Save & execute

**9A. Save weekly record**

Save to: `weeklys/YYYY-MM-DD/YYYY-MM-DD weekly.md`

**9B. Update member profiles**

For each team member with observations from the debriefing:
- Update `team/<member>/<First Last>.md` Notas section
- Add per-member observations relevant to upcoming 1:1s
- Flag topics the owner wants to address in next 1:1
- Bump `last_updated` in frontmatter

**(Only if capability `tasks` is configured)** **9C. Create tasks for ALL action items**

Use routing rules from `docs/reference/integrations.md`:
- Create tasks for the owner's items AND for every team member's items — no exceptions
- Include `Source: Weekly YYYY-MM-DD` in description
- Assign to correct owner
- Set deadline if confirmed; if no deadline discussed, ask before creating
- Set priority based on context (urgent/high/normal/low)

**EXCEPTION — Calendar action items:**
Action items involving scheduling (e.g., "marcar reunião com X"):
1. Use `find_meeting_times` to check availability
2. Create event via `create_event` (Google Meet, description, attendees)
3. Send comms DM to every attendee (except the owner) with context and purpose
4. Mark as completed in meeting record (not a task)
5. If availability unclear → fall back to task for the owner

**9D. Append decisions to context/decisions.md**

If decisions were made:
- Append to `context/decisions.md` (columns: #, Date, Decision, Context/Rationale, Impacted, Source Meeting, Tipo)
- Source Meeting format: `[[YYYY-MM-DD weekly]]`
- Classify Tipo: `estrutural` (permanent patterns) or `operacional` (execution tied to dates). When ambiguous → `estrutural`

**9E. Update owner's dev-plan**

If the owner confirmed a management development observation:
- Append to `team/<owner-slug>/<Owner Name> dev-plan.md` Situation Log

**9F. Update skills-matrix**

If competencies were discussed or demonstrated:
- Update member profile frontmatter `skills:` block (level changes, new observations)
- Update `team/skills-matrix.md` Analysis section if gaps/risks changed

**(Only if capability `comms` is configured)** **9G. Send comms canvas + DMs per member**

**Step 1 — Create ONE Canvas** with the full weekly record adapted for comms canvas-flavored Markdown:

1. Title: `Weekly do Time — YYYY-MM-DD`
2. Content: adapt the saved weekly record for Canvas format:
   - Remove YAML frontmatter
   - Convert `[[Full Name]]` wikilinks to plain text (or `![](@SLACK_ID)` for known members)
   - Keep all sections: Context, Previous Items per member, Discussion topics, Decisions, Action Items (as checklists `- [ ]`) grouped by member, Key Takeaways, Next Steps
   - Action items should use Canvas checklist format grouped by member and deadline
   - Decision audit and Team Dynamics Lens analysis are INTERNAL — do NOT include in Canvas
3. Create via `create_canvas` — save the returned `canvas_url`

**Step 2 — Send DM to each member** (excluding the owner — `<your user id from comms MCP details>`):

1. Look up member's comms ID from profile in `team/<member>/`
2. Send DM via `send_message` containing:
   - Link to the Canvas
   - **Short summary** of THIS member's action items with deadlines (not everyone's)
   - "Da liderança pra ti:" — owner's commitments relevant to this member
   - Closing: "Qualquer coisa, me chama."
3. Confirm: "Canvas criado e enviado para [list of names] no comms."

**Important:** The Canvas is the detailed record. The DM is short and actionable — just the link + that person's items.

**9H. Check next weekly scheduling**

- Query the `calendar` MCP for next weekly
- If scheduled (recurring): "Próxima weekly: [data] às [hora]."
- If NOT scheduled, **use AskUserQuestion**:
  - "Próxima weekly?"
  - Options: "Manter recorrência" / "Sugerir 3 horários" / "Não agendar"

### Step 10 — 🔍 Quality gate: propagation (parallel subagents)

First, the main thread scans ALL information consumed in this workflow — from the transcription AND from the owner's inputs during debriefing (Steps 4-6) — and builds the **propagation manifest**: a list of what needs to be propagated per category.

**Deduplication rule:** Avoid duplicating what was already written during Step 9. Focus especially on the owner's reactions, interpretations, ad-hoc decisions, and strategy shifts shared during the debriefing conversation that were NOT captured in the meeting transcript itself. Heuristic: if it was already written to a file during Step 9, skip it here.

Then, spawn **parallel agents** (model: "sonnet") for categories that have items to propagate. Only spawn agents for categories with actual work — skip empty categories.

**PEOPLE:**
□ New person mentioned in transcription? → Create profile using `templates/person.md`
  - Ask for full name, role/sector if not obvious
  - Use `search_users` for comms ID
  - Use `find_member_by_name` for tasks MCP ID
  - Add to `context/people.md` static table
□ Existing person — new info learned? → Update profile Notas section

**PROJECTS:**
□ New project mentioned? → Ask for details, create using `templates/project-context.md`
  - Create `projects/<kebab>/` folder
  - Create `projects/<kebab>/<Display Name>.md`
  - Tag: `project/<kebab>` + `project/active`
□ Existing project — status/risk/decision changed? → Update context file:
  1. Update status if changed
  2. Add meeting entry to Meetings table
  3. Append new decisions to Key Decisions (with link to this meeting)
  4. Update Risks & Blockers if new ones emerged
  5. Update Participants if new people involved
  6. Update Notes section with relevant new context

**DECISIONS:**
□ Any decision made (in meeting OR during debriefing conversation)? → Append to `context/decisions.md` with Tipo

**TASKS:**
□ All action items created via the `tasks` MCP? (verify count matches meeting record)
□ Existing tasks impacted by decisions? → Update status/assignee/deadline via the `tasks` MCP

**SKILLS & DEVELOPMENT:**
□ Competency discussed or demonstrated? → Update member profile `skills:` frontmatter
□ Owner practiced management competency? → Log to `Owner Name dev-plan.md` Situation Log

**CONTEXT FILES:**
□ Team composition changed? → Update `context/team.md`
□ Company info changed? → Update `context/company.md`
□ Something Claude needs from the owner? → Append to `context/pendings.md`

Each sub-item: if applies → execute. If not → skip explicitly. Do NOT mark completed with a vague "nothing to propagate."

**Parallel execution:** After building the manifest, spawn up to 3 agents:
- **People Agent** (`subagent_type: cos-vault-loader`) (if people items exist): Create/update profiles, lookup IDs via MCP. For external people/companies: use WebSearch to enrich profiles. Mark web-sourced info with `<!-- Source: web search YYYY-MM-DD -->`
- **Projects Agent** (`subagent_type: cos-vault-loader`) (if project items exist): Create/update project context files
- **Context Agent** (`subagent_type: cos-vault-loader`) (if context items exist): Update context/decisions.md, team.md, skills-matrix.md, pendings.md, owner's dev-plan

Main thread verifies all agent results before marking gate as completed.

If any propagation requires input (e.g., new person without clear role, new project needing details), use **AskUserQuestion** before spawning agents:
- "Encontrei [nome] na transcrição sem perfil. Quem é?" → Options based on context / "Não é relevante"
- "Projeto [X] mencionado sem context file. Criar?" → "Sim, com esses dados" / "Sim, mas corrigir" / "Não criar"

### Step 11 — Wrap-up

Relatório final:
- Weekly record saved: `<full path>`
- tasks created: list each with task name and assignee
- calendar events created: list each (if any)
- comms canvas created + DMs sent to: `<list of names>`
- Decisions appended: list each with # from context/decisions.md
- Profiles updated: list each file touched
- Projects updated: list each
- Follow-through Score: X/Y (Z%) — trend
- Next weekly: date/time or "not scheduled"
- Key follow-up topics for next meeting: 2-3 items to watch
- 1:1 topics noted: per-member list

**Obsidian**: All files created/modified MUST include YAML frontmatter per `docs/reference/conventions.md`. Use `[[wikilinks]]` for all person/project references.

## Edge Cases

- **Transcription fails**: Report error. Offer text-based alternative: "Quer me contar o resumo por texto?"
- **Audio partially inaudible**: Mark as `[inaudível]`. Ask for context with surrounding quotes.
- **Not all members spoke**: Note in debriefing. "Recomendo perguntar diretamente a [nome] na próxima weekly ou via 1:1."
- **Off-topic discussions**: Summarize briefly in record but don't expand. Note in debriefing if time management is a concern.
- **Contentious discussion captured**: Handle sensitively. Present facts, not interpretations. Ask: "Como você viu essa discussão? Precisa de follow-up individual?"
- **Very short meeting (<15 min)**: Create full record. Ask: "Foi curta. Faltou algum tópico importante? Alguém precisava de mais espaço?"
- **Member absent without notice**: Flag in debriefing. "⚠️ [nome] ausente sem aviso prévio. Tudo bem?"
- **First weekly with new member**: No history for that member. Flag: "Primeira weekly com [nome]. Observar integração."

## Quality Rules

- **Attendees**: ALWAYS list who was present and absent
- **Decisions**: Document with rationale — "decided X because Y". Never just "decidiu-se X"
- **Action items**: Every item MUST have an owner. Deadlines confirmed with the owner, not assumed
- **Factual records**: Meeting records capture what was discussed and decided. Claude's analysis (Team Dynamics Lens) goes in the debriefing conversation, NOT in the saved record — except for Coaching Moments and Team Dynamics tables which ARE saved
- **Follow-through**: ALWAYS calculate score from previous weekly. No exceptions
- **Engagement**: Do NOT fabricate engagement signals. If unclear, note absence of signal
- **Coaching Moments**: Classify honestly. If the owner solved when they could have coached, record it — the goal is awareness, not judgment
- **DM filtering**: Each member receives ONLY information relevant to them. No full meeting dump

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Transcription: `weeklys/YYYY-MM-DD/transcription.txt`
- Last weekly: most recent `YYYY-MM-DD weekly.md` in `weeklys/`
- Team profiles: `team/*/` (all member .md files)
- Owner's dev plan: `team/<owner-slug>/<Owner Name> dev-plan.md`
- Active projects: `projects/*/` (main .md files)
- Decisions: `context/decisions.md`

If a draft was generated but not saved, regenerate it from the transcription.
If debriefing already happened (Steps 5-6 completed), proceed to Step 7+ without re-presenting.
