---
name: cos-process-1on1
description: Processa transcrição de 1:1 e conduz debriefing interativo com o gestor
user-invocable: true
argument-hint: <member-name>
effort: high
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

Processar transcrição do one-on-one com $ARGUMENTS.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

IMPORTANT: Do NOT save the meeting record before debriefing. The conversation with the owner comes first.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped. Create sub-tasks dynamically as needed (e.g., one task per task to create, one per profile to update).

**Pre-flight**
0. **Load config + integration availability** — read `context/cos-config.md`, resolve tokens, toggle integrations

**Phase 1 — Collect**
1. **Transcribe audio** — run transcription script, never ask the owner for text
2. **Dependency Analysis** — analyze transcription, extract entities
3. **Load context: single-wave parallel agents** (Core + Targeted)

**Phase 2 — Analyze**
4. **Draft meeting record** — generate all sections from transcription
5. **Run management lens** — internal analysis (development, engagement, coaching, patterns, owner's practice)

**Phase 3 — Debrief**
6. ⏸️ **PAUSE: Present Block 1** — "O que eu capturei" + AskUserQuestion validation
7. ⏸️ **PAUSE: Present Block 2** — "O que me chamou atenção" + AskUserQuestion for recurrents
8. ⏸️ **PAUSE: Present Block 3** — "Minha leitura" + AskUserQuestion for dev-plan
9. **Incorporate feedback** — adjust draft with the owner's corrections from all blocks

**Phase 4 — Quality Check**
10. 🔍 **Quality gate: structure** — validate frontmatter fields, wikilinks `[[Full Name]]`, footer per conventions.md
11. 🔍 **Quality gate: content** — verify check-in captured, action items have owners+deadlines, engagement score justified
12. 🔍 **Quality gate: management sections** — feedback uses SBI framework, growth observations present, coaching moments logged, manager reflection included

**Phase 5 — Save & Execute** (one task per discrete action — create sub-tasks dynamically for multi-item steps)
13. **Save meeting record** — write to `team/<member>/meetings/YYYY-MM-DD/` with full frontmatter per conventions.md
14. **Update member profile** — edit `team/<member>/<Name>.md`: personal discoveries, notes, observations for future 1:1s
15. **Update member dev plan** — conditional: edit `team/<member>/<Name> dev-plan.md` if development areas discussed
16. **Create tasks** — one sub-task per action item extracted (`create_task` per item, route per integrations.md)
17. **Schedule calendar events** — conditional: only if scheduling actions identified (`create_event` per event, requires owner approval)
18. **Append decisions** — one entry per decision to `context/decisions.md` with sequential #, Tipo (estrutural/operacional), Source Meeting wikilink
19. **Update owner's dev-plan** — conditional: add to Situation Log in `team/<owner-slug>/<Owner Name> dev-plan.md` if the owner practiced a management competency
20. **Update skills-matrix** — conditional: update member profile frontmatter (`skills:` YAML block) if competencies discussed
21. **Send comms canvas + DM** — create Canvas with full 1:1 record adapted for Slack, then DM member with Canvas link + short summary of their action items
22. ⏸️ **Check next 1:1** — AskUserQuestion: suggest scheduling based on cadence (monthly) and open items

**Phase 6 — Propagate** (one sub-task per category with items — spawn Sonnet agents in parallel if 2+ categories)
23. 🔍 **Propagation: build manifest** — scan session for new/updated people, projects, context; classify by category
24. **Propagate: people** — conditional: create/update profiles in `people/` using `templates/person.md` (spawn agent if items exist)
25. **Propagate: projects** — conditional: create/update context files in `projects/<slug>/` using `templates/project-context.md` (spawn agent if items exist)
26. **Propagate: context files** — conditional: update `context/team.md`, `context/company.md`, `context/pendings.md`, `team/skills-matrix.md` (spawn agent if items exist)

**Phase 7 — Close**
27. **Wrap-up** — report to you: files saved, tasks created, decisions logged, profile updated, Slack sent, next steps

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
2. **RUN**: `python scripts/transcrever_audio.py "<audio_file>" $ARGUMENTS [--date YYYY-MM-DD]`
   - Script auto-creates meeting folder, moves audio, converts to WAV, transcribes via Whisper
   - Wait for it to complete (may take 1-3 min depending on audio length)
   - Only skip if `transcription.txt` ALREADY EXISTS in `team/$ARGUMENTS/meetings/YYYY-MM-DD/`
3. Read transcription from `team/$ARGUMENTS/meetings/YYYY-MM-DD/transcription.txt`

**If transcription fails:** Report the error. Offer: "Quer me contar o resumo da reunião por texto? Consigo montar o registro a partir disso."

### Step 2 — Dependency Analysis (main thread)

Analyze the transcription and extract a structured dependency list. This runs in the main thread (~5 seconds), no subagent.

**Extract:**
- **people**: Names mentioned beyond the primary participant. Check against `team/` and `people/` folders
- **projects**: Project names referenced (match against `projects/` folder names)
- **decisions_keywords**: Keywords to filter `context/decisions.md` (beyond the primary filter)
- **external_entities**: Companies, tools, partners not documented in the vault
- **slack_topics**: Specific keywords for targeted comms searches (beyond base blocker search)
- **needs_dm**: `true` if transcription mentions private conversation, DM content, or "te mandei mensagem"
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

This output feeds the Targeted portions of Step 3 agents.

### Step 3 — Load context (single-wave parallel)

Pre-calculate Unix timestamps in main thread before spawning agents:
- `seven_days_ago`: Unix timestamp for 7 days ago
- `fourteen_days_ago`: Unix timestamp for 14 days ago

Spawn ALL agents in parallel using dedicated CoS loader agents (each declares its own MCPs and tools via frontmatter):

**Agent 1 — Core vault** (`subagent_type: cos-vault-loader`):
- Read `team/$ARGUMENTS/<First Last>.md` — member profile
- Read `team/$ARGUMENTS/<First Last> dev-plan.md` — development plan
- Read last 1 meeting record from `team/$ARGUMENTS/meetings/` (most recent `YYYY-MM-DD 1on1 *.md`, NOT transcription.txt)
- Read `team/<owner-slug>/<Owner Name>.md` — owner's priorities
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — owner's management competencies
- Read `context/decisions.md` — filter for decisions involving this member
- Return: member state, dev plan status, owner's focus areas, last meeting action items + engagement scores, relevant decisions

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `templates/meeting.md` — record structure
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming
- Return: template structure, convention rules
- Note: `integrations.md` is NOT read here — static IDs are embedded directly in agent prompts. Full `integrations.md` is read later at Phase 5 (Save & Execute) for task creation routing rules.

**Agent 3 — Targeted vault** (`subagent_type: cos-vault-loader`) (only if deps have items):
- If `deps.people` has names: read their profiles from `team/` or `people/`
- If `deps.projects` has names: read their context files from `projects/<name>/<Name>.md`
- If `deps.needs_history`: read meeting records #2 and #3 from `team/$ARGUMENTS/meetings/`
- If nothing to load: skip this agent entirely
- Return: additional profiles, project context, historical meeting data

**(Only if capability `comms` is configured)** **Agent A — comms** (`subagent_type: cos-mcp-loader`):
Include in prompt: `#time` = `<team channel from comms MCP details>`, `#projetos` = `<projects channel from comms MCP details>`. Read member's `slack_id` from profile frontmatter.

Base (always):
- `read_channel` `<team channel from comms MCP details>` (oldest: `seven_days_ago`) — team activity
- `read_channel` `<projects channel from comms MCP details>` (oldest: `seven_days_ago`) — project updates
- `search_public` `from:@member "blocked" OR "stuck" OR "problema" OR "help" after:YYYY-MM-DD` — blocker signals

Targeted (from deps):
- If `deps.needs_dm`: `read_channel` DM with member (oldest: `fourteen_days_ago`)
- If `deps.slack_topics` has items: `search_public` for each topic
- For messages with `reply_count > 0` that match targeted topics: `read_thread`

Extract and classify: blockers, help requests, bypass requests, notable contributions, project updates, personal signals.
- Return: classified comms intelligence

**(Only if capability `tasks` is configured)** **Agent B — tasks** (`subagent_type: cos-mcp-loader`):
Include in prompt: Space `<workspace id from tasks MCP details>`.
- Search tasks assigned to or mentioning this member (active statuses)
- If `deps.projects` has names: also search tasks in those projects
- Return: pending tasks with status, deadlines, blockers

**Agent C — calendar** (`subagent_type: cos-mcp-loader`):
Include in prompt: timezone `<timezone from calendar MCP details>`, member email.
- List upcoming events involving this member (next 14 days)
- Return: upcoming meetings, scheduling conflicts

**WebSearch/WebFetch (main thread, after agents return):**
- If `deps.external_entities` has items not in vault: search for context

Consolidate all agent results before proceeding to Step 4.

### Step 4 — Draft meeting record + Management lens

**3A. Generate the meeting record draft internally (do NOT save yet).**

Follow `templates/meeting.md` structure. Extract from transcription:
- Personal check-in content (or note its absence)
- Previous action items status (cross-reference with last meeting)
- Topics discussed with notes
- Key takeaways
- Decisions made (with rationale and impact)
- Action items (with owners — ask for deadlines if not mentioned)
- Feedback given/received (capture in SBI format when possible)
- Growth observations (concrete, evidence-based — not generic)
- Coaching moments (Coaching / Directing / Solving classification)
- Engagement signals per dimension (with evidence, N/A if unclear)

**3B. Run Management Lens analysis internally.**

This analysis is NOT shown as a raw checklist to the owner. It enriches Blocks 2 and 3 of the debriefing.

**MEMBER DEVELOPMENT:**
- Was the dev plan discussed or referenced? If not, how long since it was last touched?
- Any competency demonstrated or discussed? (positive growth or gap)
- Was feedback given? In what format? (SBI? direct? vague? none?)
- When member brought a challenge: did the owner coach (asked questions), direct (told what to do), or solve (did it themselves)?
- Is member showing growing, stable, or declining autonomy vs last 1:1?

**ENGAGEMENT TRAJECTORY:**
- Compare each engagement dimension with last 1:1: Mood, Motivation, Workload, Satisfaction
- If any dimension dropped ≥2 points → MUST flag in debriefing Block 2
- If consistently high 3+ meetings → recognize in debriefing

**RELATIONSHIP & TRUST:**
- Did personal check-in happen? Was it genuine or just protocol?
- Did member share something personal? (trust indicator)
- How many 1:1s since the owner last asked about personal life? If 3+ → suggest personal questions in debriefing

**PATTERN DETECTION:**
- Previous action items: how many completed vs pending?
- Any item appearing 3rd+ consecutive meeting? → ⚠️ RECORRENTE — must flag in debriefing
- Recurring themes: evolution or stagnation?
- Did the owner fulfill their own commitments from last 1:1? If not → must flag in debriefing ("Você se comprometeu com X e não entregou")

**WILL'S MANAGEMENT PRACTICE:**
- Did the owner practice any competency from their dev-plan? Which one?
- Did the owner avoid a difficult topic that was pending?
- Was the owner's feedback specific (SBI) or generic/vague?
- Did the owner ask more questions or make more statements? (coaching vs telling ratio)
- Did the owner delegate or centralize?

### Step 5 — ⏸️ PAUSE: Debriefing

Present synthesis in 3 blocks, enriched by the Management Lens analysis:

**Block 1: "O que eu capturei"**
- Executive summary (5-7 lines): main topics discussed, decisions made, commitments
- Action items extracted with owners and deadlines
- **Validation**: "Confirmei que você se comprometeu com [X] até [data]. Correto?"
- If deadline wasn't mentioned for an item: ask immediately (don't silently leave blank)

**Block 2: "O que me chamou atenção"**
- Engagement signals (positive and negative) with evidence from transcript
- Engagement trajectory vs last meeting: "Motivação subiu/caiu/estável comparado com [data]"
- Patterns: "Essa é a Xª vez que [nome] menciona [tema]. Parece importante."
- ⚠️ RECORRENTE items: "Este item aparece pela Xª reunião consecutiva sem resolução. Sugiro [ação]."
- Things NOT said: "Vocês não falaram sobre [pending project/action item]. Intencional?"
- If member expressed frustration, uncertainty, or disengagement: quote specific moments
- Owner's blind spots: "Você não perguntou sobre [development area / personal topic]. Considere para próxima vez?"
- Owner's unfulfilled commitments: "No último 1:1 você se comprometeu com [X]. Foi feito?"

**Block 3: "Minha leitura" (provocation)**
- Hypothesis about the member's state: "Minha leitura: [nome] está [hypothesis]. Bate com sua percepção?"
- Engagement score rationale: "Baseado na conversa, avaliei [scores]. Dimensões sem sinais claros: N/A"
- Coaching style observation: "Nessa reunião, identifiquei X momentos coaching, Y directing, Z solving."
- Follow-up suggestion: "Recomendo [specific action] na próxima 1:1 ou antes"
- If difficult conversation happened: "Como você se sentiu sobre como abordou [tema]? O que faria diferente?"
- **Manager development (only if notable):**
  - Owner practiced competency well: "Boa abordagem em [situação]. Isso fortalece [competência]."
  - Owner missed opportunity: "Havia espaço pra [competência] quando [situação]. Como você viu isso?"
  - Ask: "Quer que eu registre no seu plano de desenvolvimento?"
  - Do NOT mention this if the meeting was routine.

**PAUSE — Use AskUserQuestion for structured validation:**

After presenting all 3 blocks, use AskUserQuestion:

```
Question 1: "Como ficou a síntese geral?"
Options: "Bate, pode salvar" / "Preciso corrigir algo" / "Quero adicionar contexto" / "Refazer análise"

Question 2 (if action items have no deadline — one per item):
"Deadline para '[action item]'?"
Options: "Esta semana" / "Próxima semana" / "Sem prazo" / "Definir data"

Question 3 (if ⚠️ RECORRENTE items detected):
"Item '[X]' aparece pela Xª vez sem resolução. Ação?"
Options: "Escalar" / "Cobrar diretamente" / "Delegar" / "Remover da pauta"

Question 4 (if manager development observation — only when notable):
"Registrar '[observação]' no seu plano de desenvolvimento?"
Options: "Sim, registrar" / "Não, foi rotina" / "Sim, mas reformular"
```

Ask as many questions as needed — no limit. Each decision point that requires your input gets its own AskUserQuestion call. Use plain text only for open exploration ("O que está na sua cabeça?") or sensitive topics.

**WAIT.** Do NOT proceed until you respond to all questions.

### Step 6 — Incorporate feedback

- Apply the owner's corrections and additions to the draft
- Note any new information shared during debriefing (decisions, context, priorities) — these feed the propagation gate later
- If the owner confirms a management development observation → note for dev-plan update
- If the owner shares self-assessment about their approach → capture for Manager Reflection section

### Step 7 — 🔍 Quality gate: record completeness

Before saving, verify each item explicitly:

**STRUCTURE:**
□ All template sections filled or explicitly marked as not applicable?
□ YAML frontmatter complete? (type: meeting, subtype: 1on1, date, participant wikilink, status, tags)
□ All person mentions use `[[Full Name]]` wikilinks?
□ All project mentions use `[[Project Display Name]]` wikilinks?
□ Navigation footer present? (`See also: [[Participant]] | [[Participant dev-plan]] | [[MOC Meetings]]`)

**CONTENT QUALITY:**
□ Personal Check-in has real content? If none happened: "Não houve check-in pessoal nesta reunião"
□ Previous Action Items reviewed with actual status from last meeting? Recurrence flags added for 3+ items?
□ Engagement scores justified by transcript evidence? (N/A where no evidence — NEVER fabricate)
□ Engagement Trend column filled comparing with last meeting? (↑ → ↓ or N/A if first meeting)

**MANAGEMENT SECTIONS:**
□ Feedback Given: in SBI format where possible? If no feedback given: note absence
□ Feedback Received: captured? If none: section empty (not removed)
□ Growth Observations: concrete and evidence-based? (not generic "está evoluindo")
□ Coaching Moments table: all moments classified? (Coaching / Directing / Solving)
□ Manager Reflection: filled if something notable happened? Empty if routine?

If any item fails → fix before proceeding. Do NOT mark this step completed with failures.

### Step 8 — Save & execute

**7A. Save meeting record**

Save to: `team/$ARGUMENTS/meetings/YYYY-MM-DD/YYYY-MM-DD 1on1 <FirstName>.md`

**7B. Update member profile**

Update `team/$ARGUMENTS/<First Last>.md`:
- Personal discoveries → Personal Profile / Dreams & Life Goals sections
- New notes → Notas section
- Member-specific observations relevant to future 1:1s → Notas section (flag for next meeting)
- Bump `last_updated` in frontmatter

**7C. Update development plan**

If development progress was discussed:
- Update `team/$ARGUMENTS/<First Last> dev-plan.md`

**(Only if capability `tasks` is configured)** **7D. Create tasks for ALL action items**

Use routing rules from `docs/reference/integrations.md`:
- Create tasks for the owner's items AND member's items — no exceptions
- Include `Source: 1:1 [member] YYYY-MM-DD` in description
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

**7E. Append decisions to context/decisions.md**

If decisions were made:
- Append to `context/decisions.md` (columns: #, Date, Decision, Context/Rationale, Impacted, Source Meeting, Tipo)
- Classify Tipo: `estrutural` (permanent patterns) or `operacional` (execution tied to dates). When ambiguous → `estrutural`

**7F. Update owner's dev-plan**

If the owner confirmed a management development observation:
- Append to `team/<owner-slug>/<Owner Name> dev-plan.md` Situation Log

**7G. Update skills-matrix**

If competencies were discussed or demonstrated:
- Update member profile frontmatter `skills:` block (level changes, new observations)
- Update `team/skills-matrix.md` Analysis section if gaps/risks changed or new pending evaluations should be added

**(Only if capability `comms` is configured)** **7H. Send comms canvas + DM to participant**

**Step 1 — Create Canvas** with the full 1:1 record adapted for comms canvas-flavored Markdown:

1. Title: `1:1 [Member Name] — YYYY-MM-DD`
2. Content: adapt the saved 1:1 record for Canvas format:
   - Remove YAML frontmatter
   - Convert `[[Full Name]]` wikilinks to plain text (or `![](@SLACK_ID)` for known people)
   - Keep all sections: Context, Discussion, Decisions, Action Items (as checklists `- [ ]`), Development observations (if appropriate to share), Key Takeaways, Next Steps
   - Coaching Moments and the owner's internal analysis are INTERNAL — do NOT include in Canvas
   - Action items should use Canvas checklist format grouped by owner
3. Create via `create_canvas` — save the returned `canvas_url`

**Step 2 — Send DM to member:**

1. Look up participant's comms ID from profile in `team/$ARGUMENTS/`
2. Send DM via `send_message` containing:
   - Link to the Canvas
   - **Short summary** of the member's action items with deadlines
   - "Da minha parte:" — what the owner committed to (so member can track)
   - Closing: "Qualquer coisa, me chama."
3. If action items/calendar events involve people outside the 1:1 → send them contextual comms DMs too (text DM is fine for third parties, Canvas is for the main participant)
4. Confirm: "Canvas criado e enviado para [nome] no comms. [Também notifiquei X sobre Y.]"

**Important:** The Canvas is the detailed record. The DM is short and actionable — just the link + key items.

**7I. Check next meeting scheduling**

- Query the `calendar` MCP for next 1:1 with this member
- If scheduled: "Próxima 1:1 com [nome]: [data] às [hora]."
- If NOT scheduled, **use AskUserQuestion**:
  - "Próxima 1:1 com [nome]?"
  - Options: "Sugerir 3 horários" / "Manter sem agendar" / "Definir manualmente"
  - If "Sugerir": query both calendars for availability, present options via AskUserQuestion with time previews, create on approval

### Step 9 — 🔍 Quality gate: propagation (parallel subagents)

First, the main thread scans ALL information consumed in this workflow — from the transcription AND from the owner's inputs during debriefing (Steps 4-5) — and builds the **propagation manifest**: a list of what needs to be propagated per category.

**Deduplication rule:** Avoid duplicating what was already written during Step 8. Focus especially on the owner's reactions, interpretations, ad-hoc decisions, and strategy shifts shared during the debriefing conversation that were NOT captured in the meeting transcript itself. Heuristic: if it was already written to a file during Step 7, skip it here.

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
- **Projects Agent** (`subagent_type: cos-vault-loader`) (if project items exist): Create/update project context files. For projects involving external tools/platforms: use WebSearch/WebFetch to gather documentation and product context
- **Context Agent** (`subagent_type: cos-vault-loader`) (if context items exist): Update context/decisions.md, team.md, skills-matrix.md, pendings.md, owner's dev-plan

Main thread verifies all agent results before marking gate as completed.

If any propagation requires input (e.g., new person without clear role, new project needing details), use **AskUserQuestion** before spawning agents:
- "Encontrei [nome] na transcrição sem perfil. Quem é?" → Options based on context / "Não é relevante"
- "Projeto [X] mencionado sem context file. Criar?" → "Sim, com esses dados" / "Sim, mas corrigir" / "Não criar"

### Step 9 — Wrap-up

Relatório final:
- Meeting record saved: `<full path>`
- tasks created: list each with task name and assignee
- calendar events created: list each (if any)
- comms canvas created + DM sent to: `<name>`
- Decisions appended: list each with # from context/decisions.md
- Profiles updated: list each file touched
- Projects updated: list each
- Next 1:1: date/time or "not scheduled — want me to suggest?"
- Key follow-up topics for next meeting: 2-3 items to watch

**Obsidian**: All files created/modified MUST include YAML frontmatter per `docs/reference/conventions.md`. Use `[[wikilinks]]` for all person/project references.

## Edge Cases

- **Transcription fails**: Report error. Offer text-based alternative: "Quer me contar o resumo por texto?"
- **Audio partially inaudible**: Mark `[inaudível]` in draft. Ask for context with surrounding quotes.
- **Very short meeting** (<10 min): Create full record. Ask: "Foi uma reunião curta. Está tudo bem com [nome]? Algo que deveria ter sido discutido?"
- **Emotional or tense meeting**: Lead debriefing with care: "Pareceu uma conversa intensa. Como você está se sentindo sobre isso?"
- **First meeting with member**: No history to compare. Engagement trends = N/A. Focus on initial impressions and what to explore next.

## Quality Rules

- **Engagement Check**: Score ONLY based on conversation signals. N/A when unclear. NEVER fabricate.
- **Action items**: Every item MUST have an owner. Deadlines confirmed with the owner, not assumed.
- **Personal discoveries**: Update profile only with factual info shared by the member.
- **Factual records**: Meeting records capture what was said and decided. Claude's interpretations go in the debriefing conversation, NOT in the saved meeting.md file.
- **Coaching Moments**: Classify honestly. If the owner solved when they could have coached, record it — the goal is awareness, not judgment.
- **Manager Reflection**: Only fill when genuinely notable. Do NOT force observations on routine meetings.

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Transcription: `team/$ARGUMENTS/meetings/YYYY-MM-DD/transcription.txt`
- Member profile: `team/$ARGUMENTS/<First Last>.md`
- Dev plan: `team/$ARGUMENTS/<First Last> dev-plan.md`
- Last meeting: most recent `YYYY-MM-DD 1on1 *.md` in `team/$ARGUMENTS/meetings/`
- Owner's dev plan: `team/<owner-slug>/<Owner Name> dev-plan.md`

If a draft was generated but not saved, regenerate it from the transcription.
If debriefing already happened (Step 5 completed), proceed to Step 6+ without re-presenting.
