---
name: cos-process-meeting
description: Processa transcricao de reuniao de projeto/demanda e conduz debriefing interativo com o gestor
user-invocable: true
argument-hint: <project-name>
effort: high
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

## Brand Voice

Esta skill produz texto que será lido pelo gestor/owner, e em algumas seções escreve no nome dele (debriefing, recomendações, perguntas).

**Antes de gerar qualquer texto, consultar `context/will-brand-voice.md`.**

3 regras-chave para esta skill especificamente:
1. **Pronome**: "a gente" como 1ª plural, "você" singular dirigindo-se ao gestor. Nunca "nós".
2. **Sem platitudes**: substituir frases motivacionais vazias por dado nomeado, contra-case concreto, ou afirmação afiada. Ver §13 do voice file.
3. **Concisão direta**: o gestor não cushiona feedback. Recomendações são imperativas ("vale a pena perguntar X", "sugiro Y") — não cushioned ("talvez você queira considerar...").

---

Processar transcricao de reuniao de projeto ou demanda com $ARGUMENTS.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

IMPORTANT: Do NOT save the meeting record before debriefing. The conversation with the owner comes first.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped. Create sub-tasks dynamically as needed (e.g., one task per task to create, one per profile to update).

**Pre-flight**
0. **Load config + integration availability** — read `context/cos-config.md`, resolve tokens, toggle integrations

**Phase 1 — Collect**
1. **Identify context** — ask for project, participants, standalone detection
2. **Transcribe audio** — run transcription script, never ask the owner for text
3. **Dependency Analysis** — analyze transcription, extract entities
4. **Load context: single-wave parallel agents** (Core + Targeted)

**Phase 2 — Analyze**
5. **Draft meeting record** — generate all sections from transcription (do NOT save)
6. **Run Project Lens** — internal analysis (health, stakeholders, decisions, owner's practice)

**Phase 3 — Debrief**
7. ⏸️ **PAUSE: Present Block 1** — "O que capturei" + AskUserQuestion validation
8. ⏸️ **PAUSE: Present Block 2** — "O que me chamou atenção" + AskUserQuestion for recurrents
9. ⏸️ **PAUSE: Present Block 3** — "Minha leitura" + AskUserQuestion for dev-plan
10. ⏸️ **PAUSE: Present Block 4** — "Cross-impact" + AskUserQuestion for workload
11. ⏸️ **PAUSE: Present Block 5** — "Decision audit" + AskUserQuestion for deferred decisions
12. **Incorporate feedback** — adjust draft with the owner's corrections

**Phase 4 — Quality Check**
13. 🔍 **Quality gate: Record Quality** — structure + content completeness
14. 🔍 **Quality gate: Decision Quality** — rationale, classification, decider

**Phase 5 — Save & Execute** (one task per discrete action — create sub-tasks dynamically for multi-item steps)
15. **Save meeting record** — write to `projects/<slug>/meetings/YYYY-MM-DD/` with full frontmatter per conventions.md
16. **Update project context file** — add meeting row to meetings table, update status/risks/notes in `projects/<slug>/<Project>.md`
17. **Create tasks** — one sub-task per action item extracted (`create_task` per item, route per integrations.md)
18. **Schedule calendar events** — conditional: only if scheduling actions identified (`create_event` per event, requires owner approval)
19. **Append decisions** — one entry per decision to `context/decisions.md` with sequential #, Tipo (estrutural/operacional), Source Meeting wikilink
20. **Update owner's dev-plan** — conditional: add to Situation Log in `team/<owner-slug>/<Owner Name> dev-plan.md` if the owner practiced a management competency
21. **Update skills-matrix** — conditional: update member profile frontmatter (`skills:` YAML block) if competencies discussed
22. **Send comms canvas + DM** — create Canvas with full meeting record adapted for Slack, then DM each participant with Canvas link + short summary of their action items
23. ⏸️ **Check next meeting** — AskUserQuestion: suggest scheduling follow-up based on open items

**Phase 6 — Propagate** (one sub-task per category with items — spawn Sonnet agents in parallel if 2+ categories)
24. 🔍 **Propagation: build manifest** — scan session for new/updated people, projects, context; classify by category
25. **Propagate: people** — conditional: create/update profiles in `people/` using `templates/person.md` (spawn agent if items exist)
26. **Propagate: projects** — conditional: create/update context files in `projects/<slug>/` using `templates/project-context.md` (spawn agent if items exist)
27. **Propagate: context files** — conditional: update `context/team.md`, `context/company.md`, `context/pendings.md`, `team/skills-matrix.md` (spawn agent if items exist)

**Phase 7 — Close**
28. **Wrap-up** — report to you: files saved, tasks created, decisions logged, profiles updated, Slack sent, next steps

## Process

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill uses integrations: **slack, clickup** (plus always-on vault and references).

- Resolve all `{{...}}` tokens from the config "Integration IDs" table.
- Toggle `false` → skip; `true` → test MCP, skip-with-warning if unavailable.
- Never stop processing for a missing integration. The transcription + vault context always produce the meeting record; integrations only enrich (task creation, Slack cross-reference).
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-first.

### Step 1 — Identify context

1. If `$ARGUMENTS` is provided, use it as the project name
2. If not provided, ask: "Qual projeto ou tema dessa reunião?"
3. Ask: "Quem participou?" (if not provided)
4. **Standalone detection**: After transcription (or if multi-topic is indicated), analyze content:
   - If 2+ distinct projects identified without one being clearly dominant:
     → Use AskUserQuestion: "Identifiquei que essa reunião tocou em [Project A, B, C]. Como classificar?"
     → Options: "Standalone (multi-projeto)" / "É do projeto [A]" / "É do projeto [B]" / "Outro"
   - If standalone is confirmed → fork to **Standalone Flow** (see below)
   - If it belongs to one project → continue normal flow
5. **Resolve project folder**: Run `ls projects/` and find the EXACT existing folder name BEFORE calling the script. If a folder already exists with the same or similar name (e.g. `pacote-planilhas` vs `pacote-de-planilhas`), use the EXISTING name. Only create a new kebab-case name if no existing folder matches
6. If first meeting for this project:
   - Create `projects/<project-name>/` directory
   - Create `projects/<project-name>/<Project Display Name>.md` from `templates/project-context.md`
7. If "it's not really a project" is confirmed, suggest a descriptive name anyway. Examples: `problema-api-whatsapp`, `pedido-sistema-eventos`

### Step 2 — Transcribe audio

**You MUST run the transcription script before doing ANYTHING else.** Do NOT ask the owner for the transcription text. Do NOT skip this step.

1. Find the audio file: search for `Recording*.m4a` (or .mp3/.wav) in the vault root, or ask for the path
2. **RUN**: `python scripts/transcrever_audio.py "<audio_file>" --type project --project <project-name> [--date YYYY-MM-DD]`
   - Script auto-creates meeting folder, moves audio, converts to WAV, transcribes via Whisper
   - Script has fuzzy matching on project folder names as a safety net
   - Wait for it to complete (may take 1-3 min depending on audio length)
   - Only skip if `transcription.txt` ALREADY EXISTS in `projects/<project-name>/meetings/YYYY-MM-DD/`
3. Read transcription from `projects/<project-name>/meetings/YYYY-MM-DD/transcription.txt`

**If transcription fails:** Report the error. Offer: "Quer me contar o resumo da reunião por texto? Consigo montar o registro a partir disso."

### Step 3 — Dependency Analysis (main thread)

Analyze the transcription and extract a structured dependency list. This runs in the main thread (~5 seconds), no subagent.

The participant list from Step 1 defines Core profiles. People mentioned in transcription but NOT in the participant list go to Targeted.

**Extract:**
- **people**: Names mentioned beyond participants from Step 1. Check against `team/` and `people/` folders
- **projects**: Additional project names referenced beyond the primary project (match against `projects/` folder names)
- **decisions_keywords**: Keywords to filter `context/decisions.md` (beyond the project filter)
- **external_entities**: Companies, tools, partners not documented in the vault
- **slack_topics**: Specific keywords for targeted comms searches (beyond base blocker search)
- **needs_dm**: `true` if transcription mentions private conversation or DM content
- **needs_history**: `true` if transcription references prior meetings ("da última vez", "a gente combinou", "como ficou aquilo")

**Output format** (internal, not shown to user):

```
deps = {
  people: [],
  projects: [],
  decisions_keywords: [],
  external_entities: [],
  slack_topics: [],
  needs_dm: false,
  needs_history: false
}
```

This output feeds the Targeted portions of Step 4 agents.

### Step 4 — Load context (single-wave parallel)

Pre-calculate Unix timestamps in main thread before spawning agents:
- `seven_days_ago`: Unix timestamp for 7 days ago
- `fourteen_days_ago`: Unix timestamp for 14 days ago

Spawn ALL agents in parallel using dedicated CoS loader agents (each declares its own MCPs and tools via frontmatter):

**Agent 1 — Core vault** (`subagent_type: cos-vault-loader`):
- Read `projects/<project-name>/<Display Name>.md` — project context, history, risks
- Read last 1 meeting record from `projects/<project-name>/meetings/` (most recent `YYYY-MM-DD *.md`, NOT transcription.txt)
- Read profiles of all participants from Step 1 (from `team/` and `people/`)
- Read `team/<owner-slug>/<Owner Name>.md` — owner's priorities
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — owner's management competencies
- Read `context/decisions.md` — filter for decisions involving this project
- If standalone: read ALL referenced projects' context files (identified in Step 1)
- Return: project state, last meeting action items, participant profiles, owner's focus areas, relevant decisions

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `templates/project-meeting.md` (or `templates/standalone-meeting.md` if standalone) — record structure
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming
- Return: template structure, convention rules
- Note: `integrations.md` is NOT read here — static IDs in agent prompts. Full `integrations.md` at Phase 5.

**Agent 3 — Targeted vault** (`subagent_type: cos-vault-loader`) (only if deps have items):
- If `deps.people` has names not in participant list: read their profiles from `team/` or `people/`
- If `deps.projects` has names not already loaded (non-standalone): read their context files
- If `deps.needs_history`: read meeting records #2 and #3 from `projects/<project-name>/meetings/`
- If nothing to load: skip this agent entirely
- Return: additional profiles, project context, historical meeting data

**(Only if capability `comms` is configured)** **Agent A — comms** (`subagent_type: cos-mcp-loader`):
Include in prompt: `#time` = `<team channel from comms MCP details>`, `#projetos` = `<projects channel from comms MCP details>`.

Base (always):
- `read_channel` `<projects channel from comms MCP details>` (oldest: `seven_days_ago`) — project updates
- `read_channel` `<team channel from comms MCP details>` (oldest: `seven_days_ago`) — team activity
- `search_public` `"project name" "blocked" OR "stuck" OR "problema" after:YYYY-MM-DD` — project blocker signals

Targeted (from deps):
- If `deps.slack_topics` has items: `search_public` for each topic
- For messages with `reply_count > 0` that match targeted topics: `read_thread`
- No DM reads unless `deps.needs_dm: true`

Extract and classify: blockers, project updates, stakeholder dynamics, unanswered messages.
- Return: classified comms intelligence for this project

**(Only if capability `tasks` is configured)** **Agent B — tasks** (`subagent_type: cos-mcp-loader`):
Include in prompt: Space `<workspace id from tasks MCP details>`.
- Active tasks for this project (current statuses, overdue, blocked)
- Tasks assigned to meeting participants
- If `deps.projects` has names: tasks in those projects too
- Return: tasks snapshot with status, deadlines, blockers

**Agent C — calendar** (`subagent_type: cos-mcp-loader`):
Include in prompt: timezone `<timezone from calendar MCP details>`.
- Upcoming meetings for this project (next 14 days)
- Return: upcoming meetings, scheduling conflicts

**WebSearch/WebFetch (main thread, after agents return):**
- If `deps.external_entities` has items not in vault: search for context

Consolidate all agent results before proceeding to Step 5.

### Step 5 — Draft meeting record + Project Lens

**4A. Generate the meeting record draft internally (do NOT save yet).**

Follow `templates/project-meeting.md` structure. Extract from transcription:
- Project context at time of meeting (status, milestone, previous meeting reference)
- Previous action items status (cross-reference with last meeting)
- Discussion topics with detailed notes
- Technical decisions with rationale and impact
- Risks & blockers with severity and owner
- Stakeholder Dynamics (who led, active, passive, absent)
- Decision Audit (reactive/proactive, alternatives, decider)
- Cross-Impact (other projects affected, resource implications, timeline dependencies)
- Action items with owners (ask for deadlines if not mentioned)
- Key takeaways
- Next steps

**4B. Run Project Lens analysis internally.**

This analysis is NOT shown as a raw checklist to the owner. It enriches Blocks 2-5 of the debriefing.

**DIMENSION 1 — Project Health:**
- Status real vs declared: On Track / At Risk / Blocked — evidence-based from transcription
- Velocity: previous action items completion rate (% done vs pending)
- Unaddressed risks: identified by CoS (from project context.md) but not discussed in meeting
- Scope creep: new demands without impact assessment on timeline
- Deadline pressure: mentions of urgency, delays, missed dates
- Trend: comparing with last 2-3 meetings — improving, stable, or worsening?

**DIMENSION 2 — Stakeholder Dynamics:**
- Who led the conversation (approximate % of talk time, who set the agenda)
- Who stayed silent or passive
- Tensions or misalignments between participants
- Real vs apparent alignment: genuine agreement or "letting it pass"?
- Participants who should have been present but weren't (based on project context.md)

**DIMENSION 3 — Decision Quality:**
- Each decision: reactive (responding to problem) or proactive (anticipating)?
- Alternatives discussed or "first option accepted"?
- Who actually decided (hierarchy, consensus, or one person imposed)?
- Information basis: sufficient data or deciding blind?
- Decisions deferred/avoided that should have been made

**WILL'S MANAGEMENT PRACTICE (only when notable):**
- Delegated or centralized during the meeting?
- Asked the right questions or accepted what was presented?
- Addressed risks or avoided conflict?
- Dev-plan competency practiced? (link to specific competency)

### Step 6 — ⏸️ PAUSE: Debriefing

Present synthesis in 5 blocks, enriched by the Project Lens analysis:

**Block 1: "O que capturei"**
- Meeting objective and whether it was achieved
- Executive summary by topic (5-7 lines)
- Technical decisions with rationale
- Action items extracted with owners and deadlines
- Validation: "Confirmei que [nome] ficou responsável por [X] até [data]. Correto?"
- If deadline wasn't mentioned for an item: ask immediately (don't silently leave blank)

**Use AskUserQuestion:**

```
Question 1: "Como ficou a captura?"
Options: "Bate, pode avançar" / "Preciso corrigir fatos" / "Quero adicionar contexto" / "Refazer"

Question 2 (per action item without deadline):
"Deadline para '[action item]'?"
Options: "Esta semana" / "Próxima semana" / "Sem prazo" / "Definir data"
```

**WAIT.** Do NOT proceed until you respond.

**Block 2: "O que me chamou atenção"**
- Risks identified or implied during the meeting (fed by Lens dimension 1)
- Cross-meeting patterns: "Esse é o Xº encontro sobre [projeto] e [padrão persiste]"
- Blockers needing escalation
- Things NOT discussed that should have been (based on project context.md)
- ⚠️ RECORRENTE for action items appearing 3+ times without progress
- Owner's blind spots: "Você não perguntou sobre [risco/tema pendente]"
- Owner's unfulfilled commitments from last meeting (if applicable)

**Use AskUserQuestion:**

```
Question 1 (if ⚠️ RECORRENTE items detected, one per item):
"Item '[X]' aparece pela Xª vez sem resolução. Ação?"
Options: "Escalar" / "Cobrar diretamente" / "Delegar" / "Remover da pauta"
```

**WAIT.** Do NOT proceed until you respond.

**Block 3: "Minha leitura"**
- Project health assessment: On Track / At Risk / Blocked with justification
- Stakeholder dynamics (fed by Lens dimension 2): "Quem dominou, quem ficou quieto"
- Suggestions for next steps beyond what was discussed
- Follow-up suggestion: "Recomendo [specific action] antes da próxima reunião"
- Manager development (only if notable):
  - Owner practiced competency well: "Boa abordagem em [situação]. Fortalece [competência]."
  - Owner missed opportunity: "Havia espaço pra [competência] quando [situação]. Como você viu isso?"
  - Ask: "Quer que eu registre no seu plano de desenvolvimento?"
  - Do NOT mention this if the meeting was routine

**Use AskUserQuestion:**

```
Question 1: "Bate com sua leitura do projeto?"
Options: "Sim" / "Discordo do status" / "Quero adicionar contexto"

Question 2 (if manager development observation, only when notable):
"Registrar '[observação]' no seu plano de desenvolvimento?"
Options: "Sim, registrar" / "Não, foi rotina" / "Sim, mas reformular"
```

**WAIT.** Do NOT proceed until you respond.

**Block 4: "Cross-impact"**
- Other projects affected by this meeting's decisions
- Team workload: "[nome] aparece em [projeto A] e [projeto B] — carga ok?"
- Timeline dependencies between projects
- Shared resources at risk
- Vague commitments: "[nome] disse que vai 'ver' — recomendo pedir ETA concreto"

**Use AskUserQuestion:**

```
Question 1: "Algum cross-impact que eu não identifiquei?"
Options: "Não, tá completo" / "Adicionar impacto" / "Remover item"
```

**WAIT.** Do NOT proceed until you respond.

**Block 5: "Decision audit"**
- Each decision classified: reactive vs proactive
- Alternatives considered (or "nenhuma discutida — primeira opção aceita")
- Actual decider identified per decision
- Decisions avoided/deferred that deserved attention
- Pattern over time: "Últimas X reuniões deste projeto: Y% decisões reativas" (if history available)

**Use AskUserQuestion:**

```
Question 1: "Audit de decisões bate?"
Options: "Sim, pode salvar" / "Corrigir classificação" / "Adicionar decisão que não capturei"
```

**WAIT.** Do NOT proceed until you respond to all blocks.

### Step 7 — Incorporate feedback

- Apply the owner's corrections and additions to the draft
- Note any new information shared during debriefing (decisions, context, priorities) — these feed the propagation gate later
- If the owner confirmed a management development observation → note for dev-plan update
- If the owner corrected project status → update in draft
- If the owner added cross-impact items → update Cross-Impact section

### Step 8 — 🔍 Quality gate: Record Quality

Before saving, verify each item explicitly:

**STRUCTURE:**
□ All template sections filled or explicitly marked as not applicable?
□ YAML frontmatter complete? (type: meeting, subtype: project, date, project wikilink, participants, status, tags)
□ All person mentions use `[[Full Name]]` wikilinks?
□ All project references use `[[Project Display Name]]` wikilinks?
□ Navigation footer present? (`See also: [[Project Name]] | [[MOC Meetings]] | [[MOC Projects]]`)

**CONTENT:**
□ Project Context section filled with current status and milestone?
□ Previous Action Items reviewed with actual status from last meeting? Recurrence flags for 3+?
□ Every action item has an owner?
□ Every risk has severity and owner?
□ Project status (On Track / At Risk / Blocked) with justification?
□ Stakeholder Dynamics table filled for all participants?
□ Decision Audit table filled for all decisions?
□ Cross-Impact section filled (or explicit "Nenhum impacto cruzado identificado")?
□ Participants listed match transcription?
□ Inaudible sections marked with `[inaudível]`?

If any item fails → fix before proceeding. Do NOT mark this step completed with failures.

### Step 9 — 🔍 Quality gate: Decision Quality

Before saving, verify:

□ Every decision has rationale documented (not just "decidiu-se X")?
□ Every decision classified as reactive or proactive?
□ Alternatives recorded (or explicit "nenhuma discutida")?
□ Decider identified for each decision?
□ Tipo assigned: estrutural or operacional?

If any item fails → fix before proceeding.

### Step 10 — Save & execute

**9A. Save meeting record**

Save to: `projects/<project-name>/meetings/YYYY-MM-DD/YYYY-MM-DD <project-kebab>.md`

**9B. Update project context file**

Update `projects/<project-name>/<Display Name>.md`:
- Bump "Last Updated" date
- Update project status if changed
- Add entry to Meetings table (date, summary, link to record)
- Append decisions to Key Decisions table (with link to this meeting)
- Update Risks & Blockers if new ones emerged
- Add new participants if first time appearing
- Update Notes section with relevant new context

**(Only if capability `tasks` is configured)** **9C. Create tasks for ALL action items**

Use routing rules from `docs/reference/integrations.md`:
- Create tasks for the owner's items AND for every participant's items — no exceptions
- Include `Source: Reunião [project-name] YYYY-MM-DD` in description
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
- Source Meeting format: `Reunião [project-name] YYYY-MM-DD`
- Classify Tipo: `estrutural` (permanent patterns) or `operacional` (execution tied to dates). When ambiguous → `estrutural`

**9E. Update owner's dev-plan**

If the owner confirmed a management development observation:
- Append to `team/<owner-slug>/<Owner Name> dev-plan.md` Situation Log

**9F. Update skills-matrix**

If competencies were discussed or demonstrated:
- Update member profile frontmatter `skills:` block (level changes, new observations)
- Update `team/skills-matrix.md` Analysis section if gaps/risks changed

**(Only if capability `comms` is configured)** **9G. Send comms canvas + DMs per participant**

**Step 1 — Create ONE Canvas** with the full meeting record adapted for comms canvas-flavored Markdown:

1. Title: `[Meeting type] [Project] — YYYY-MM-DD` (e.g., "Weekly Project X — 2026-04-23")
2. Content: adapt the saved meeting record for Canvas format:
   - Remove YAML frontmatter
   - Convert `[[Full Name]]` wikilinks to plain text (or `![](@SLACK_ID)` for known participants)
   - Keep all sections: Context, Previous Items, Discussion, Decisions, Risks, Action Items (as checklists), Key Takeaways, Next Steps
   - Action items should use Canvas checklist format (`- [ ] item`) grouped by priority/deadline
   - Decision Audit and Project Lens are INTERNAL — do NOT include in Canvas
   - Cross-Impact: include only if relevant to participants
3. Create via `create_canvas` — save the returned `canvas_url`

**Step 2 — Send DM to each participant** (excluding the owner — `<your user id from comms MCP details>`):

1. Look up participant's comms ID from profile in `team/` or `people/`
2. Send DM via `send_message` containing:
   - Link to the Canvas
   - **Short summary** of THIS person's action items with deadlines (not everyone's)
   - Closing: "Qualquer coisa, me chama."
3. For external participants (no comms ID): skip and note
4. Confirm: "Canvas criado e enviado para [list of names] no comms. [External participants] não receberam (sem comms ID)."

**Important:** The Canvas is the detailed record. The DM is short and actionable — just the link + that person's items.

**9H. Check next meeting scheduling**

- Query the `calendar` MCP for next meeting of this project
- If recurring: "Próxima reunião de [project]: [data] às [hora]."
- If NOT scheduled, **use AskUserQuestion**:
  - "Próxima reunião de [project]?"
  - Options: "Sugerir 3 horários" / "Manter sem agendar" / "Definir manualmente"
  - If "Sugerir": query calendars for availability, present options via AskUserQuestion, create on approval

### Step 11 — 🔍 Quality gate: propagation (parallel subagents)

First, the main thread scans ALL information consumed in this workflow — from the transcription AND from the owner's inputs during debriefing (Steps 5-6) — and builds the **propagation manifest**: a list of what needs to be propagated per category.

**Deduplication rule:** Avoid duplicating what was already written during Step 10. Focus especially on the owner's reactions, interpretations, ad-hoc decisions, and strategy shifts shared during the debriefing conversation that were NOT captured in the meeting transcript itself. Heuristic: if it was already written to a file during Step 10, skip it here.

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
- **People Agent** (`subagent_type: cos-vault-loader`) (if people items exist): Create/update profiles, lookup IDs via MCP. For external people/companies: use WebSearch to enrich profiles (role, company info, LinkedIn context). Mark web-sourced info with `<!-- Source: web search YYYY-MM-DD -->`
- **Projects Agent** (`subagent_type: cos-vault-loader`) (if project items exist): Create/update project context files. For projects involving external tools/platforms: use WebSearch/WebFetch to gather documentation
- **Context Agent** (`subagent_type: cos-vault-loader`) (if context items exist): Update context/decisions.md, team.md, skills-matrix.md, pendings.md, owner's dev-plan

Main thread verifies all agent results before marking gate as completed.

If any propagation requires input (e.g., new person without clear role, new project needing details), use **AskUserQuestion** before spawning agents:
- "Encontrei [nome] na transcrição sem perfil. Quem é?" → Options based on context / "Não é relevante"
- "Projeto [X] mencionado sem context file. Criar?" → "Sim, com esses dados" / "Sim, mas corrigir" / "Não criar"

### Step 12 — Wrap-up

Relatório final:
- Meeting record saved: `<full path>`
- Project context updated: `<project file path>`
- tasks created: list each with task name and assignee
- calendar events created: list each (if any)
- comms canvas created + DMs sent to: `<list of names>` (note external participants skipped)
- Decisions appended: list each with # from context/decisions.md
- Profiles updated: list each file touched
- Projects updated: list each
- Next meeting: date/time or "not scheduled — want me to suggest?"
- Key follow-up topics for next meeting: 2-3 items to watch

**Obsidian**: All files created/modified MUST include YAML frontmatter per `docs/reference/conventions.md`. Use `[[wikilinks]]` for all person/project references.

---

## Standalone Flow

When Step 1 confirms a standalone meeting (2+ projects, no single dominant), follow this adapted flow instead of the normal process.

### Standalone Pre-Phase

1. Claude asks/suggests the category via AskUserQuestion:
   - "Qual a categoria dessa reunião?"
   - Options: "Alinhamento" / "Estratégica" / "Ad-hoc" / "Diretoria"
2. Owner confirms or adjusts
3. Destination: `projects/standalone-meetings/meetings/YYYY-MM-DD/`

### Standalone Step 2 — Transcription

1. **RUN**: `python scripts/transcrever_audio.py <audio_file> --type project --project standalone-meetings [--date YYYY-MM-DD]`
   - No script modifications needed — pseudo-project folder treated like any other
2. After transcription, rename auto-generated record file to: `YYYY-MM-DD <category> <short-description>.md`
3. Read transcription from `projects/standalone-meetings/meetings/YYYY-MM-DD/transcription.txt`

### Standalone Step 3 — Load context

Same 2-wave strategy, but:
- **Vault Agent** reads context files for ALL projects referenced in the transcription
- **Reference Agent** reads `templates/standalone-meeting.md` instead of `project-meeting.md`
- MCP agents query across all referenced projects

### Standalone Step 5 — Draft + Lens

- Draft follows `templates/standalone-meeting.md` — discussions organized BY PROJECT
- Project Lens runs at portfolio level: cross-project health, resource conflicts, strategic coherence

### Standalone Debriefing (Steps 5)

Same 5-block structure, adapted for multi-project:

**Block 1: "O que capturei"**
- Organized by project: "Sobre o [Projeto A] capturei X. Sobre o [Projeto B] capturei Y."
- Decisions and action items grouped by project
- Validation of owners and deadlines per project

**Block 2: "O que me chamou atenção"**
- Cross-project analysis: resource conflicts, timeline dependencies, competing priorities
- Patterns across meetings: "Xº encontro onde [pattern]"
- Things NOT discussed per project (based on each project's context.md)

**Block 3: "Minha leitura"**
- Portfolio-level health: holistic view across all projects discussed
- Resource allocation: "[nome] aparece em [projeto A] e [projeto B] — carga ok?"
- Strategic coherence: do the decisions align across projects?

**Block 4: "Cross-impact"**
- Between the projects discussed specifically (not external)
- Shared resources and timeline overlap

**Block 5: "Decision audit"**
- Same structure but with Project column per decision

### Standalone Save & Propagate

1. **Save standalone record**: `projects/standalone-meetings/meetings/YYYY-MM-DD/YYYY-MM-DD <category> <description>.md`
2. **Propagate to each project in `projects_discussed`:**
   - Add entry to Meetings table: `YYYY-MM-DD | 1-2 line summary | [[YYYY-MM-DD category description]]`
   - Update Key Decisions (source → standalone meeting name)
   - Update Risks & Blockers
   - Update Notes if new info from this meeting
3. **Create tasks** for ALL action items (routing rules from `docs/reference/integrations.md`)
   - Tasks created once from standalone record — NOT duplicated per project
   - Route each task to the correct project's task list using the Project column
   - Include "Source: [Meeting title] YYYY-MM-DD" in description
4. **Append decisions** to `context/decisions.md` with Source: "[Meeting title] YYYY-MM-DD"
5. People, profiles, skills-matrix — identical to normal flow
6. **Next meeting check** — same as normal flow

Confirm: "Tudo salvo. Informações propagadas para [list of projects]. Próximo passo: [key follow-up]."

Then continue with comms DMs (Step 10G) and Propagation gate (Step 11) as normal.

---

## Edge Cases

- **Transcription fails**: Report error. Offer text-based alternative: "Quer me contar o resumo por texto?"
- **Audio partially inaudible**: Mark `[inaudível]` in draft. Ask for context with surrounding quotes
- **Very short meeting (<10 min)**: Create full record. Ask: "Foi uma reunião rápida. Resolveu o que precisava?"
- **First meeting for project**: Create `context.md`, ask for project background if not evident from transcription
- **Meeting spans multiple projects**: Standalone detection triggers automatically (Step 1). If overridden to assign to one project, that project gets the full record and others get cross-references in propagation
- **External participants present**: Note carefully what was said, flag anything with external implications. External participants without comms ID are skipped in DMs — noted to the owner
- **Recurring project meeting**: Reference previous meeting's action items for review
- **Project name changes**: Keep original folder name. Note the name change in `context.md`
- **Overlap with 1:1 or weekly**: Distinguishing factor is purpose — project progress vs personal development vs team status. Ask if unclear
- **Emotional or tense meeting**: Lead debriefing with care: "Pareceu uma conversa intensa. Como você está vendo o projeto?"
- **Contentious discussion captured**: Handle sensitively. Present facts, not interpretations. Ask: "Como você viu essa discussão? Precisa de follow-up individual?"

## Quality Rules

- **NO engagement scores** — this is not a 1:1. Do not fabricate engagement data
- **NO personal check-in section** — this is project-focused
- **Decisions**: Document with rationale — "decided X because Y". Never just "decidiu-se X"
- **Action items**: Every item MUST have an owner. Deadlines confirmed with the owner, not assumed
- **Factual records**: Meeting records capture what was discussed and decided. Claude's analysis (Project Lens, Decision Audit internals) goes in the debriefing conversation, NOT in the saved record — except for Stakeholder Dynamics, Decision Audit, and Cross-Impact tables which ARE saved
- **External stakeholders**: Note what was shared vs what should remain internal
- **Coaching classification**: Not applicable for project meetings (no Coaching Moments table)
- **DM filtering**: Each participant receives ONLY information relevant to them. Decision Audit and Project Lens are INTERNAL — never shared
- **Inaudible sections**: Mark as `[inaudível]` — do not fill gaps with assumptions

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Transcription: `projects/<project-name>/meetings/YYYY-MM-DD/transcription.txt`
- Project context: `projects/<project-name>/<Display Name>.md`
- Last meetings: most recent records in `projects/<project-name>/meetings/`
- Participant profiles: `team/` and `people/` for each participant
- Owner's dev plan: `team/<owner-slug>/<Owner Name> dev-plan.md`
- Decisions: `context/decisions.md`

If a draft was generated but not saved, regenerate it from the transcription.
If debriefing already happened (Step 6 completed), proceed to Step 7+ without re-presenting.
