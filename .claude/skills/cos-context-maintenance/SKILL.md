---
name: cos-context-maintenance
description: Executa manutencao de contexto — varredura profunda do vault com cross-reference externo, guided refresh interativo com você e aplicacao de atualizacoes
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

Executar manutenção de contexto periódica do vault CoS — varredura profunda, cross-reference com fontes externas, guided refresh interativo com você, auto-archive de context/decisions.md.

This skill is the single source of truth for the **periodic context maintenance** workflow.
All instructions, cross-reference logic, quality gates, auto-archive rules, staleness detection, and edge cases are here.

**Scope:** This skill covers the periodic check-up, auto-archive, and staleness detection. Session-sync is a separate skill (`cos-session-sync`). Continuous maintenance (post-workflow propagation) is handled by the Universal Propagation Gate in each V2 workflow.

IMPORTANT: This is a conversation, not a report. Present findings first, ask questions about gaps, then apply changes only after você confirms. Claude should be **proactive** — cross-reference external sources, detect divergences the user hasn't noticed, and request depth on shallow profiles.

CRITICAL: Create ONE task per checklist item. Do NOT bundle multiple items into a single task. Each numbered item below = exactly 1 TaskCreate call. Dynamic sub-tasks (e.g., one per file to update, one per profile to enrich) are created in addition to the checklist tasks.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped.

**Pre-flight**
0. **Load config + integration availability** — read cos-config.md, resolve tokens, check integration toggles

**Phase 1 — Collect**
1. **Load context: vault files** — spawn agent (Wave 1)
2. **Load context: references** — spawn agent (Wave 1, parallel with #1)
3. **Load context: comms** — spawn dedicated agent (Wave 2)
4. **Load context: tasks** — spawn dedicated agent (Wave 2, parallel with #3)
5. **Load context: calendar** — spawn dedicated agent (Wave 2, parallel with #3)
6. **Load context: email** — spawn dedicated agent (Wave 2, parallel with #3)

**Phase 2 — Audit**
7. **Cross-reference: vault vs tasks** — projects, tasks, status divergences
8. **Cross-reference: vault vs comms** — decisions, announcements, role changes, new info
9. **Cross-reference: vault vs calendar** — meeting records coverage
10. **Cross-reference: vault vs email** — stakeholder communications, org changes
11. **Quality audit: profile completeness** — empty fields, shallow profiles, missing sections
12. **Quality audit: dev-plan activity** — recent situations, stale goals, inactive plans
13. **Quality audit: staleness check** — last_updated thresholds per file category
14. **Memory curation** — audit MEMORY.md index and detail files for staleness, accuracy, and relevance
15. **Compile Vault Health Score** — 6-dimension dashboard (Freshness, Completeness, Consistency, Depth, Dev-plan Activity, Meeting Coverage)
16. 🔍 **Quality gate: Audit Completeness** — verify all sources queried and cross-references executed

**Phase 3 — Present Findings**
17. **Present divergences + gaps + staleness + quality issues** — organized by priority
18. **Present Vault Health Score dashboard** — consolidated view
19. ⏸️ **PAUSE 1: Direction** — AskUserQuestion: how to proceed with findings

**Phase 4 — Guided Refresh**
20. **Apply auto-corrections** — divergences with no ambiguity (status updates, factual corrections)
21. **Guided refresh: Time** — questions about team gaps (roles, responsibilities, projects)
22. **Guided refresh: Projects** — questions about project gaps (new projects, status changes, missing context files)
23. **Guided refresh: Company** — questions about org/company gaps (structure, products, strategy, stack)
24. **Guided refresh: Você** — questions about the owner's dev-plan, priorities, OKRs, recent practice
25. **Guided refresh: Memory** — present stale/outdated memory items, ask o gestor to confirm or update
26. **Guided refresh: Depth** — proactive requests for more info on shallow profiles, incomplete sections
27. ⏸️ **PAUSE 2: Confirm enrichments** — AskUserQuestion: validate refresh answers

**Phase 5 — Execute**
28. **Apply all confirmed updates** — one dynamic sub-task per file modified
29. **Apply memory updates** — update/remove/consolidate memory files per curation findings
30. **Run auto-archive evaluation** — scan context/decisions.md for archivable entries
31. **Execute archive** — move qualifying decisions to context/decisions-archive.md (if conditions met)
32. 🔍 **Quality gate: Deduplication** — verify no duplicate information introduced

**Phase 6 — Validate**
33. ⏸️ **PAUSE 3: Validation** — present summary of all changes, AskUserQuestion for approval
34. 🔍 **Quality gate: Vault Health Score (after)** — re-run Health Score, compare before vs after

**Phase 7 — Propagate & Close**
35. 🔍 **Quality gate: propagation — build manifest** — scan all info from audit + the owner's inputs during refresh
36. **Propagate: people** — create/update profiles (spawn agent if items exist)
37. **Propagate: projects** — create/update context files (spawn agent if items exist)
38. **Propagate: context files** — decisions, team, company, pendings, skills (spawn agent if items exist)
39. **Update pendings.md** — append unresolved gaps from guided refresh
40. **Wrap-up** — report everything audited, updated, archived, and propagated

## Process

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill uses integrations: **slack, clickup, calendar, gmail** (plus always-on vault and references).

- Resolve all `{{...}}` tokens from the config "Integration IDs" table.
- Toggle `false` → skip that integration's calls; `true` → test MCP, skip-with-warning if unavailable.
- Never stop maintenance for a missing integration. The vault scan always runs; integrations only add external cross-reference.
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-first.

### Step 1 — Load context: vault files (Wave 1)

Spawn agent (model: "sonnet"). This agent runs in parallel with Step 2.

**Agent 1 — Vault files** (`subagent_type: cos-vault-loader`):
- Read `team/<owner-slug>/<Owner Name>.md` — the owner's profile, priorities, OKRs
- Read `team/<owner-slug>/<Owner Name> dev-plan.md` — the owner's management competencies, Situation Log
- Read ALL member profiles from `team/*/` — frontmatter (skills, last_updated) + Notas + Personal Profile sections
- Read ALL member dev-plans from `team/*/` — progress, recent situations
- Read `context/team.md` — current team composition
- Read `context/company.md` — org structure, products, stack
- Read `context/people.md` — people directory
- Read `team/skills-matrix.md` — competency dashboard, gaps, change log
- Read `context/decisions.md` — full decision log (check last #, count entries, identify potential archive candidates)
- Read `context/decisions-archive.md` — verify exists, check last archived entry
- Read `context/pendings.md` — open items
- Read last 3 meeting records per member (most recent `YYYY-MM-DD *.md` in `team/*/meetings/` and `weeklys/`, NOT transcription.txt)
- Read all project context files from `projects/*/` — status, last updated, key decisions
- For each file: extract `last_updated` from frontmatter, note empty/missing fields
- Return: complete vault state snapshot with timestamps, empty fields, gap inventory, decisions count, archive candidates

### Step 2 — Load context: references (Wave 1)

Spawn agent (model: "sonnet"). This agent runs in parallel with Step 1.

**Agent 2 — References** (`subagent_type: cos-references-loader`):
- Read `docs/reference/integrations.md` — task routing rules, IDs, statuses, comms channel IDs
- Read `docs/reference/conventions.md` — frontmatter rules, tags, naming patterns, required fields per file type
- Read `templates/person.md` — required fields for person profiles
- Read `templates/project-context.md` — required fields for project context files
- Return: routing rules, convention rules, required field lists per file type, tasks MCP IDs, comms channel IDs

**Consolidate Wave 1 results before proceeding to Steps 3-6.**

### Steps 3-6 — Load context: external sources (Wave 2)

After Wave 1 completes, spawn **4 dedicated agents in parallel** (model: "sonnet" for all). Each agent focuses exclusively on one external system. Pass routing rules from Agent 2 (References) into each agent's prompt.

Create one task per agent. All 4 run in parallel.

**CRITICAL — Pre-calculate comms timestamps before spawning agent:**

The `read_channel` from the comms MCP tool requires Unix epoch timestamps (seconds). Subagents MUST NOT calculate these themselves — they consistently get the year wrong.

**Before spawning the comms agent**, the main thread MUST:
1. Run Bash to calculate the correct Unix timestamps for the lookback window:
   - `python -c "from datetime import datetime, timedelta; t = datetime.now() - timedelta(days=14); print(int(t.timestamp()))"`
   - (use `python3` if `python` not available)
2. Pass the **pre-calculated numeric timestamp** to the comms agent prompt as a literal value (e.g., `oldest: 1773716400`)
3. NEVER pass relative descriptions like "14 days ago" — always pass the computed number

**(Only if capability `comms` is configured)** **Step 3 — comms agent** (`subagent_type: cos-mcp-loader`):

Layer 1 — Channel reads (paginate if >100 msgs to cover full window):
- `read_channel` `#time` (oldest: `<pre-calculated 14-day timestamp>`)
- `read_channel` `#projetos` (oldest: `<pre-calculated 14-day timestamp>`)
- `read_channel` `#empresa` (oldest: `<pre-calculated 14-day timestamp>`)
- `read_channel` DM with each team member (oldest: `<pre-calculated 14-day timestamp>`)

Layer 2 — Targeted searches (`search_public`, paginate if >20 results):
- `"new project" OR "novo projeto" OR "novo sistema" after:YYYY-MM-DD` — new projects
- `"role change" OR "mudou de cargo" OR "promoção" OR "novo cargo" after:YYYY-MM-DD` — role changes
- `"decisão" OR "decidimos" OR "ficou definido" after:YYYY-MM-DD` — decisions that may be missing from context/decisions.md
- Per team member: `from:@member after:YYYY-MM-DD sort:timestamp` — member activity
- `from:@<your handle from comms MCP details> after:YYYY-MM-DD` — the owner's DMs for context on priorities

Layer 3 — Thread expansion:
- For messages with `reply_count > 0` from Layer 1/2 that seem substantive, use `read_thread` for full context

Layer 4 — Semantic search:
- `"mudanças organizacionais" in:#empresa after:YYYY-MM-DD`
- `"novo parceiro" OR "nova parceria" after:YYYY-MM-DD`
- `"saiu da empresa" OR "novo colaborador" after:YYYY-MM-DD`

Return: **classified comms intelligence** — announcements, decisions, role changes, new projects, org changes, partner news, anything that should be reflected in vault context files but may not be.

**(Only if capability `tasks` is configured)** **Step 4 — ClickUp agent** (`subagent_type: cos-mcp-loader`):
- `clickup_get_workspace_hierarchy` — full project/list structure
- `task_search` for active projects — compare names/statuses with vault `projects/*/` files
- `filter_tasks` for recently completed tasks (last 30 days) — verify project status updates propagated
- `filter_tasks` for tasks assigned to o gestor and team members — compare with vault profiles (current projects)
- Return: task project/task map with statuses, recently completed items, divergences from vault state

**(Only if capability `calendar` is configured)** **Step 5 — Calendar agent** (`subagent_type: cos-mcp-loader`):
- `list_events` past 30 days — all meetings o gestor attended (1:1s, weeklys, project meetings)
- `list_events` next 14 days — upcoming events that may need prep or context
- Cross-reference past meetings with meeting types: 1:1 (member name in title), weekly, project meeting
- Return: list of past meetings (for record coverage check) + upcoming meetings (for context enrichment needs)

**(Only if capability `email` is configured)** **Step 6 — email agent** (`subagent_type: cos-mcp-loader`):
- `search_messages` last 14 days — stakeholder communications, partner emails, org announcements
- For relevant emails: `read_message` to extract key content
- Focus: partnership changes, org structure announcements, billing/admin changes, external stakeholder context
- Return: relevant emails classified (org change / partner update / stakeholder context / admin)

Consolidate all Wave 2 agent results before proceeding to Step 7.

### Steps 7-10 — Cross-reference vault vs external sources

For each cross-reference, compare vault state (from Step 1) against external data (from Steps 3-6). Identify:
- **Divergences**: vault says X, external says Y (e.g., project status mismatch)
- **Gaps**: info exists externally but not in vault (e.g., new project via the `tasks` MCP without context file)
- **Stale refs**: vault references something that no longer exists externally

**Step 7 — Vault vs tasks:**
- Compare each vault `projects/*/` file status with task project status
- Identify task projects without vault context files
- Identify vault project files referencing task projects that are archived/deleted
- Compare team member profiles' "current projects" with task assignments
- Flag: status divergences, missing context files, orphaned references

**Step 8 — Vault vs comms:**
- Scan comms data for decisions that should be in context/decisions.md but aren't
- Identify role changes or new responsibilities mentioned via the `comms` MCP but not in profiles
- Detect new projects or initiatives discussed via the `comms` MCP without vault context files
- Flag organizational changes announced in #empresa not reflected in company.md
- Flag: missing decisions, unupdated profiles, missing project files, stale org info

**Step 9 — Vault vs calendar:**
- For each meeting in calendar past 30 days, check if a corresponding meeting record exists:
  - 1:1 meetings → `team/<member>/meetings/YYYY-MM-DD/` should have a `.md` record
  - Weeklys → `weeklys/` should have a record
  - Project meetings → `projects/<project>/meetings/` or `projects/standalone-meetings/` should have a record
- Count: meetings with records vs meetings without records
- For upcoming meetings (next 14 days): check if prep materials exist or if context is needed
- Flag: unrecorded meetings (with dates and participants), upcoming meetings needing prep

**(Only if capability `email` is configured)** **Step 10 — Vault vs email:**
- Scan email data for org changes, partner updates, or stakeholder context not reflected in vault
- Check if any email mentions new companies/people that should have profiles
- Flag: unreflected org changes, missing company/person profiles, outdated partner info

### Steps 11-13 — Quality audit

**Step 11 — Profile completeness:**

For each member profile in `team/*/` and each person in `people/`, check against `templates/person.md` required fields:
- Frontmatter: all required fields present and non-empty? (name, role, email, type, slack_id, clickup_id, skills)
- Content sections: Personal Profile, Dreams & Life Goals, Notas — have real content or are empty?
- Depth assessment: count lines of substantive content (excluding headers and boilerplate)
- Skills frontmatter: all categories present? Levels assigned? Any `null` or missing items?
- Flag: empty required fields, shallow profiles (<5 lines of notes), missing skills assessments

For each project in `projects/*/`, check against `templates/project-context.md`:
- Frontmatter: status, owner, stakeholders present?
- Content: Overview, Key Decisions, Risks & Blockers, Meetings table — filled or empty?
- Flag: incomplete project context files

**Step 12 — Dev-plan activity:**

For each member dev-plan in `team/*/`:
- Last situation logged — how many days ago?
- Goals/competencies: any stale (no progress noted in 60+ days)?
- Quarterly review: is there a recent review, or is it overdue?
- Flag: inactive dev-plans (no situations in 30+ days), stale goals, missing quarterly reviews

For the owner's dev-plan (`team/<owner-slug>/<Owner Name> dev-plan.md`):
- Same checks + is the Situation Log being actively used?
- Management competencies: any stale (no practice logged in 30+ days)?
- Flag: the owner's own development stagnation

**Step 13 — Staleness check:**

For each context file, compute days since `last_updated` in frontmatter:

| File/Category | Threshold | Flag level |
|---------------|-----------|------------|
| `context/company.md` | 30+ days | 🟡 Medium |
| `context/team.md` | 30+ days | 🟡 Medium |
| `team/<owner-slug>/<Owner Name>.md` | 30+ days | 🔴 High |
| `Owner Name dev-plan.md` | 30+ days | 🔴 High |
| Member profiles with meetings since last update | 30+ days | 🔴 High |
| Member profiles without meetings | 60+ days | 🟡 Medium |
| `team/skills-matrix.md` | 30+ days | 🟡 Medium |
| `context/people.md` (static sections) | 60+ days | 🟢 Low |
| Project context files (active projects) | 14+ days | 🟡 Medium |
| Project context files (completed/paused) | 90+ days | 🟢 Low |

Additional staleness check:
- If meetings were processed recently (check meeting record dates) but `context/decisions.md` has no entries with those dates → flag: "Possíveis decisões não registradas nas reuniões de [datas]"

### Step 14 — Memory curation

Audit `memory/MEMORY.md` and all detail files in `memory/` for staleness, accuracy, and relevance.

**Read all memory files** — MEMORY.md index + every `memory/*.md` detail file.

**For each memory entry, evaluate:**

| Check | Criteria | Action |
|-------|----------|--------|
| **Stale project context** | Project memory references dates, deadlines, or statuses that have passed | Mark for verification with o gestor in Step 25 |
| **Completed project** | Project is done (e.g., workflow upgrades complete) | Consider removing or archiving the detail file |
| **Index line inaccurate** | MEMORY.md one-liner doesn't match detail file content | Update index line |
| **Duplicate with vault** | Memory duplicates info already in context files or CLAUDE.md | Remove — vault is source of truth |
| **Orphan detail file** | Detail file exists but no entry in MEMORY.md | Add entry or delete file |
| **MEMORY.md capacity** | Index approaching 200 lines | Prioritize: feedback > project > reference. Remove lowest-value entries |

**Classify each entry:**
- ✅ **Current** — feedback rules, permanent references, active context
- ⚠️ **Verify** — project context with passed deadlines or events
- 🗑️ **Remove** — completed projects, duplicated info, stale context no longer useful

**Output:** List of proposed memory actions (verify/update/remove) for presentation in Step 17 and guided refresh in Step 25.

### Step 15 — Compile Vault Health Score

Consolidate all audit findings into a 6-dimension dashboard:

**1. Freshness** (% of files updated within threshold)
- Count files within threshold / total files per category
- Score: >80% = 🟢, 50-80% = 🟡, <50% = 🔴

**2. Completeness** (% of required fields filled)
- Count filled required fields / total required fields across all profiles and projects
- Score: >90% = 🟢, 70-90% = 🟡, <70% = 🔴

**3. Consistency** (vault agrees with external sources)
- Count divergences found in Steps 7-10
- Score: 0 divergences = 🟢, 1-3 = 🟡, 4+ = 🔴

**4. Depth** (profiles have useful content beyond boilerplate)
- Count profiles with >10 lines of substantive notes / total profiles
- Score: >80% = 🟢, 50-80% = 🟡, <50% = 🔴

**5. Dev-plan Activity** (dev-plans actively used)
- Count dev-plans with situations logged in last 30 days / total dev-plans
- Score: >80% = 🟢, 50-80% = 🟡, <50% = 🔴

**6. Meeting Coverage** (meetings have records)
- Count meetings with records / total meetings from the `calendar` MCP
- Score: >90% = 🟢, 70-90% = 🟡, <70% = 🔴

Store this as the **baseline** for comparison in Step 31.

### Step 16 — 🔍 Quality gate: Audit Completeness

Before presenting findings, verify each item explicitly:

□ All context files scanned? (team.md, company.md, people.md, skills-matrix.md, pendings.md, context/decisions.md, the owner's profile, the owner's dev-plan)
□ All member profiles read? (frontmatter + content sections)
□ All member dev-plans read?
□ All project context files read?
□ All 4 external sources queried or degradation noted? (tasks, comms, calendar, email)
□ Cross-reference vault↔tasks executed?
□ Cross-reference vault↔comms executed?
□ Cross-reference vault↔Calendar executed?
□ Cross-reference vault↔email executed?
□ Quality audit: profile completeness executed?
□ Quality audit: dev-plan activity executed?
□ Quality audit: staleness check executed?
□ Vault Health Score compiled?

**Degradation rules** — if any MCP source fails, degrade gracefully:
- ClickUp fails → "[ClickUp indisponível — cross-reference de projetos não realizado]"
- Slack fails → "[Slack indisponível — cross-reference de decisões/anúncios não realizado]"
- Calendar fails → "[Calendar indisponível — cobertura de reuniões não verificada]"
- email fails → "[email indisponível — comunicações externas não verificadas]"

Note degradation in findings but do NOT block the workflow. Local vault audit is always valid.

If any audit step was skipped without degradation reason → fix before presenting.

### Step 17 — Present divergences + gaps + staleness + quality issues

Present findings organized by priority level:

**🔴 Critical (requires immediate action):**
- Status divergences between vault and tasks (project shows "em andamento" but ClickUp says "concluído")
- Role changes detected via the `comms` MCP but not in profiles
- Decisions found via the `comms` MCP not present in context/decisions.md
- Missing meeting records for recent meetings

**🟡 Important (should address today):**
- Stale context files (>30 days without update)
- Shallow profiles (required fields empty, <5 lines of notes)
- Inactive dev-plans (no situations in 30+ days)
- New projects via the `tasks` MCP without vault context files
- Skills assessments missing or outdated

**🟢 Informational (can defer):**
- Minor field omissions in non-critical files
- People directory entries without full context
- Low-priority staleness (completed project files)

Format each finding as:
```
[PRIORITY] [AREA] Description
  Vault: [current state]
  External: [external state] (source: [ClickUp/Slack/Calendar/email])
  Suggested fix: [what Claude recommends]
```

### Step 18 — Present Vault Health Score dashboard

Present the 6-dimension Health Score in a table:

```
| Dimensão | Score | Detalhe |
|----------|-------|---------|
| Freshness | 🟡 62% | 8/13 files atualizados nos últimos 30 dias |
| Completeness | 🟢 91% | 3 campos vazios em 34 totais obrigatórios |
| Consistency | 🔴 5 divergências | Projetos: 2, Decisões: 2, Roles: 1 |
| Depth | 🟡 60% | 3/5 profiles com profundidade adequada |
| Dev-plan Activity | 🔴 33% | 1/3 dev-plans com situações nos últimos 30 dias |
| Meeting Coverage | 🟡 75% | 9/12 reuniões com registro no vault |
```

### Step 19 — ⏸️ PAUSE 1: Direction

Use AskUserQuestion:

```
Question 1: "Encontrei X achados (Y críticos, Z importantes). Como quer proceder?"
Options:
- "Aplicar correções óbvias + perguntar sobre gaps" (Recommended) — Claude fixes unambiguous divergences and asks about the rest
- "Revisar item por item antes de qualquer mudança" — você reviews each finding before Claude acts
- "Aplicar tudo automaticamente" — Claude fixes everything without further questions
- "Só o relatório hoje" — STOP here, save gaps to pendings.md and wrap up
```

If você chooses "Só o relatório hoje" → jump to Step 36 (update pendings.md with unresolved gaps) and Step 37 (wrap-up). Skip Phases 4-6.

**WAIT.** Do NOT proceed until você responds.

### Step 20 — Apply auto-corrections

For divergences with **no ambiguity** (factual corrections from authoritative sources):
- Project status in vault doesn't match tasks → update vault to match tasks (ClickUp is source of truth for project status)
- Profile role doesn't match official Slack announcement → update profile
- `last_updated` dates that are clearly wrong → correct

For each auto-correction, create a dynamic sub-task and execute:
- Read the target file
- Apply the correction
- Bump `last_updated` in frontmatter
- Log: "Auto-corrigido: [file] — [what changed] (fonte: [source])"

**Do NOT auto-correct ambiguous items** — these go to the guided refresh (Steps 20-24).

### Steps 21-26 — Guided refresh

For each area, present the remaining gaps (not auto-corrected) and ask o gestor using AskUserQuestion. Claude should be **proactive** — ask for information the vault needs, not just confirm what it already has.

**Step 20 — Time:**

Questions about team member gaps. Use AskUserQuestion for each gap:
- "O perfil de [nome] mostra [cargo/projetos]. Ainda é isso?" → Sim / Mudou / Não sei
- "Encontrei [nome] mencionado no Slack fazendo [atividade] que não está no perfil. Adicionar?" → Sim / Não é relevante
- "[Nome] não tem avaliação de [competência]. Qual o nível atual (1-5)?" → Options with level descriptions
- "Alguma mudança no time que eu não peguei?" → Free text

**Step 21 — Projects:**

Questions about project gaps. Use AskUserQuestion for each:
- "Projeto [X] existe no `tasks` MCP mas não tem context file no vault. Criar?" → Sim com dados / Não é relevante / Já foi absorvido por outro projeto
- "Projeto [X] está como [status A] no vault mas [status B] no `tasks` MCP. Qual é o correto?" → Vault / ClickUp / Outro status
- "Encontrei discussões sobre [tema] no Slack que parece ser um projeto novo. É?" → Sim, criar / Não, é parte de [projeto existente] / Não é projeto
- "Projeto [X] sem update há [N] dias. Qual o status atual?" → Options based on standard statuses

**Step 22 — Company:**

Questions about company/org gaps:
- "Detectei [mudança organizacional] no Slack/email. company.md reflete isso?" → Sim / Precisa atualizar / Não confirmo
- "Novos stakeholders ou parceiros mencionados em [fonte] que eu deveria conhecer?" → Free text
- "Alguma mudança no tech stack, ferramentas ou processos desde [last_updated]?" → Free text
- "Algum setor novo ou reestruturação que não está no organograma?" → Free text

**Step 23 — Você:**

Questions about the owner's state and development:
- "Seu dev-plan não tem situações logadas nos últimos [N] dias. Alguma prática de gestão recente que valha registrar?" → Sim, vou descrever / Não houve nada notável / Revisar competências
- "Suas prioridades mudaram desde [last_updated]? O perfil mostra [prioridades atuais]." → Ainda são essas / Mudaram / Atualizar parcialmente
- "Como estão seus OKRs/metas para Q[X]? Algum ajuste?" → On track / Precisa ajustar / Quero revisar
- If stale >60 days: "Faz [N] dias sem atualizar seu plano de desenvolvimento. Quer revisitar as competências e goals?" → Sim, vamos revisar / Não agora

**Step 25 — Memory:**

Present memory curation findings from Step 14. For each ⚠️ Verify item, use AskUserQuestion:

- "[Memory item] referencia [evento/data/status] que já passou. Ainda é relevante?" → "Atualizar com novo status" / "Remover — já não importa" / "Manter como está"
- "Projeto [X] no memory foi concluído. Remover a memória?" → "Sim, remover" / "Manter como referência histórica" / "Consolidar com outro"

For 🗑️ Remove candidates, present list: "Estas memórias parecem obsoletas: [list]. Posso remover?"

For MEMORY.md index lines that are inaccurate, fix automatically (no approval needed — it's just a summary line).

**Step 26 — Depth:**

Proactive requests for more info on shallow profiles. For each shallow profile:
- "O perfil de [nome] está raso — só tem [N] linhas de notas. Pode me contar mais sobre: [lista de campos específicos vazios — ex: estilo de comunicação, motivações, pontos fortes, áreas de desenvolvimento]?" → Free text
- "Não temos info sobre os objetivos pessoais/sonhos de [nome]. Sabe algo?" → Sim / Nunca conversamos sobre isso / Perguntar na próxima 1:1
- "[Nome] não tem notas de observação para a próxima reunião. Algo que quer abordar?" → Sim / Nada específico

No limit on questions — ask everything needed for vault completeness. The goal is to make the vault as rich and useful as possible.

### Step 25 — ⏸️ PAUSE 2: Confirm enrichments

Present a summary of all information gathered during the refresh:

```
Coletei as seguintes informações no refresh:
- Time: [summary of team changes/additions]
- Projetos: [summary of project updates]
- Empresa: [summary of company updates]
- Você: [summary of the owner's updates]
- Profundidade: [summary of depth enrichments]
```

Use AskUserQuestion:

```
Question 1: "Confirma essas informações pra eu aplicar?"
Options:
- "Tudo certo, aplicar" — proceed to Phase 5
- "Preciso corrigir algo" — você corrects, then re-present
- "Adicionar mais contexto" — você adds info, then re-present
```

**WAIT.** Do NOT proceed until você responds.

### Step 26 — Apply all confirmed updates

For each confirmed update, create a **dynamic sub-task** and execute:

- Read the target file
- Apply the update (edit existing content or add new sections)
- Bump `last_updated` in frontmatter
- Ensure YAML frontmatter follows `docs/reference/conventions.md` rules
- Use `[[wikilinks]]` for all person/project references
- Log each change: "[file] — [what changed]"

Group updates by file — if multiple changes go to the same file, apply them all in one edit.

**For new files** (new person profiles, new project context files):
- Use the appropriate template (`templates/person.md`, `templates/project-context.md`)
- For external people/companies: use WebSearch to enrich profiles before creating (role, company info, LinkedIn context). Mark web-sourced info with `<!-- Source: web search YYYY-MM-DD -->`
- Lookup IDs: `search_users` for comms ID, `find_member_by_name` for tasks MCP ID
- Ask o gestor for any missing required fields before creating

### Step 27 — Run auto-archive evaluation

Scan `context/decisions.md` for archivable entries.

**A decision is archivable when BOTH are true:**
1. **Age:** 90+ days old (based on Date column)
2. **Project status:** Source Meeting references a project with status `concluído` or `cancelado` in its project context file, OR the decision is not linked to any active project

**Never archive:**
- Decisions with `Tipo = estrutural` — these are permanent patterns
- Decisions linked to projects with status `em andamento`, `planejamento`, or `bloqueado`

**Execution:**
1. For each decision in context/decisions.md:
   - Calculate age from Date column
   - If age < 90 days → skip
   - If `Tipo = estrutural` → skip
   - Read Source Meeting column → identify project → check project status in `projects/<project>/`
   - If project is active → skip
   - If both conditions met → add to archive list
2. Report: "Encontrei X decisões arquiváveis: [brief list]"

### Step 28 — Execute archive

**If no decisions to archive → mark as completed, skip.**

If decisions to archive:
1. Read `context/decisions-archive.md`
2. Move qualifying rows from `context/decisions.md` to `context/decisions-archive.md` (append to table, preserve original #)
3. **Do NOT renumber** remaining decisions in context/decisions.md — numbers are stable IDs referenced across the vault. Gaps in numbering are expected. New decisions get next sequential number after the highest existing one
4. Update `last_updated` in both files' frontmatter
5. Report: "Archivei X decisões operacionais para context/decisions-archive.md: [brief list with # and topics]"

No approval gate — archive logic is deterministic.

### Step 29 — Apply memory updates

Apply the owner's decisions from Step 25 (Memory guided refresh):

**For items marked "Remover":**
- Delete the detail file from `memory/`
- Remove the corresponding line from `memory/MEMORY.md`

**For items marked "Atualizar":**
- Update the detail file content with new status/info
- Update the MEMORY.md index line to reflect current state

**For items marked "Consolidar":**
- Merge content into the target file
- Delete the source file
- Update MEMORY.md to remove the merged entry

**For MEMORY.md index lines that are inaccurate** (detected in Step 14):
- Update the one-liner to match current detail file content

**Capacity check:** If MEMORY.md exceeds 150 lines after updates, prioritize retention:
1. Feedback (permanent behavioral rules) — highest retention
2. Active project context — keep only if project is ongoing
3. References — keep if still used
4. Completed project context — lowest retention, remove first

### Step 30 — 🔍 Quality gate: Deduplication

After all updates applied, verify:

□ No duplicate information between existing content and new additions? (Check: same fact stated in multiple places within a file)
□ Conflicting updates resolved? (If vault said X and comms said Y, the confirmed version is now consistent across all references)
□ `context/decisions.md` has no duplicate entries after any appends?
□ Profiles don't have repeated info across different sections? (e.g., same note in both Notas and Personal Profile)
□ Cross-references consistent? (If a project status was updated, all files referencing that project show the same status)

If any duplication found → fix before proceeding. Create dynamic sub-task for each fix.

### Step 31 — ⏸️ PAUSE 3: Validation

Present summary of all changes made:

```
Apliquei X atualizações nesta manutenção:

**Auto-correções:** (Step 19)
- [file]: [change] (fonte: [source])

**Refresh guiado:** (Step 26)
- [file]: [change]

**Archivamento:** (Step 28)
- X decisões movidas para context/decisions-archive.md

**Novos arquivos:** (if any)
- [file]: [description]
```

Use AskUserQuestion:

```
Question 1: "Revisão das mudanças. Tudo certo?"
Options:
- "Tudo certo, propagar" — proceed to Phase 7
- "Preciso corrigir algo" — você identifies issues, Claude fixes
- "Mostrar detalhes de [arquivo]" — Claude shows the full diff for a specific file
```

**WAIT.** Do NOT proceed until você responds.

### Step 32 — 🔍 Quality gate: Vault Health Score (after)

Re-run the 6-dimension Health Score with the same methodology as Step 14, but now reflecting the post-maintenance state.

Present the **before vs after comparison**:

```
| Dimensão | Antes | Depois | Delta |
|----------|-------|--------|-------|
| Freshness | 🟡 62% | 🟢 85% | +23% |
| Completeness | 🟢 91% | 🟢 97% | +6% |
| Consistency | 🔴 5 | 🟢 0 | -5 divergências |
| Depth | 🟡 60% | 🟡 80% | +20% |
| Dev-plan Activity | 🔴 33% | 🟡 67% | +34% |
| Meeting Coverage | 🟡 75% | 🟡 75% | — (não processável via maintenance) |
```

If any dimension is still 🔴 after maintenance → note why (e.g., "Meeting Coverage requer processamento individual das reuniões, não é resolúvel via maintenance").

### Step 33 — 🔍 Propagation: build manifest

Scan ALL information consumed during this workflow — from the audit data AND from the owner's inputs during the guided refresh (Steps 20-25) — and build the propagation manifest.

**Deduplication rule:** Avoid duplicating what was already written during Steps 19-26. Focus especially on:
- The owner's ad-hoc comments during the refresh that revealed new context
- Strategy shifts or priority changes o gestor mentioned but that weren't directly part of a gap question
- Decisions made during the maintenance conversation itself (e.g., "vamos cancelar esse projeto")
- New information about people that came up during depth questions

**PEOPLE:**
□ New person mentioned during refresh? → Create profile using `templates/person.md`
□ Existing person — new info from the owner's answers? → Update profile
□ Need IDs? → `search_users` / `find_member_by_name`

**PROJECTS:**
□ New project mentioned? → Create context using `templates/project-context.md`
□ Existing project — status/risk/decision changed during conversation? → Update context file

**DECISIONS:**
□ Any decision made during the maintenance conversation? → Append to `context/decisions.md` with Tipo

**TASKS:**
□ Action items from the maintenance? → Create/update via the `tasks` MCP
□ Follow-up tasks identified? → Create via the `tasks` MCP

**SKILLS & DEVELOPMENT:**
□ Competency discussed or updated during refresh? → Update member profile `skills:` frontmatter
□ The owner shared management practice insights? → Log to `Owner Name dev-plan.md` Situation Log

**CONTEXT FILES:**
□ Team composition changed during refresh? → `context/team.md` (if not already updated in Step 26)
□ Company info changed? → `context/company.md` (if not already updated)
□ Something Claude needs from o gestor? → `context/pendings.md`

### Steps 36-38 — Parallel propagation agents

Spawn agents (model: "sonnet") only for categories with actual work. Skip categories with nothing to propagate.

**Step 33 — People Agent** (`subagent_type: cos-vault-loader`) (if people items exist):
- Create/update profiles in `team/` and `people/`
- Lookup Slack/tasks MCP IDs via MCP
- For external people/companies: use WebSearch to enrich profiles
- Mark web-sourced info with `<!-- Source: web search YYYY-MM-DD -->`

**Step 34 — Projects Agent** (`subagent_type: cos-vault-loader`) (if project items exist):
- Create/update project context files in `projects/`
- For projects involving external tools: use WebSearch for context

**Step 35 — Context Agent** (`subagent_type: cos-vault-loader`) (if context items exist):
- Update `context/decisions.md`, `context/team.md`, `context/company.md`
- Update `team/<owner-slug>/<Owner Name> dev-plan.md` if applicable
- Update member profile `skills:` frontmatter if applicable

Main thread verifies all agent results before marking propagation gate as completed.

### Step 39 — Update pendings.md

Append any unresolved gaps from the guided refresh to `context/pendings.md`:
- Questions o gestor couldn't answer ("Não sei") → "Descobrir [info] sobre [pessoa/projeto]"
- Items deferred for later → "Revisar [item] na próxima maintenance"
- Follow-up actions that require external input → "Confirmar [info] com [pessoa]"
- Depth requests o gestor deferred → "Perguntar [nome] sobre [tópico] na próxima 1:1"

### Step 40 — Wrap-up

Report to o gestor:

```
Manutenção de contexto concluída.

**Vault Health Score:**
| Dimensão | Antes → Depois |
[comparison table]

**Resumo:**
- X divergências corrigidas (auto + guiadas)
- Y campos preenchidos / profiles enriquecidos
- Z decisões archivadas
- W novos arquivos criados
- N itens propagados
- P pendências registradas para próxima vez

**Próxima manutenção sugerida:** [date — 30 days from now, or sooner if Health Score has 🔴 dimensions]
```

**Obsidian**: All files created/modified MUST include YAML frontmatter per `docs/reference/conventions.md`. Use `[[wikilinks]]` for all person/project references.

## Staleness Detection

This section defines proactive staleness checks that Claude runs at session start (outside of the periodic maintenance workflow). When staleness is detected, Claude suggests running `/cos-context-maintenance`.

**Checks:**
- If `context/company.md` hasn't been updated in 30+ days → "company.md está há X dias sem atualização. Quer rodar context maintenance?"
- If `team/<owner-slug>/<Owner Name>.md` hasn't been updated in 30+ days → "Seu perfil está há X dias sem atualização. Quer rodar context maintenance?"
- If a member's profile hasn't been updated in 30+ days AND there have been meetings since → "Tivemos X reuniões com [nome] desde a última atualização do perfil. Quer rodar context maintenance?"
- If `Owner Name dev-plan.md` hasn't been updated in 30+ days → "Faz X dias sem registros no seu plano de desenvolvimento. Quer revisitar?"
- If `team/skills-matrix.md` hasn't been updated in 30+ days → "Faz X dias sem atualizar a skills matrix. Quer revisar?"
- If meetings were processed recently but `context/decisions.md` has no entries for those dates → "Possíveis decisões não registradas. Quer verificar?"

These checks are lightweight (frontmatter reads only) and don't require the full maintenance workflow.

## Auto-Archive Reference

### Tipo Classification

When appending new decisions (in any workflow), Claude assigns Tipo:
- `estrutural` — permanent patterns, standards, process rules, recurring structures (e.g., "JSDoc como padrão", "pedidos passam pelo gestor")
- `operacional` — execution decisions tied to specific dates, tasks, or one-time actions (e.g., "contestar NFS-e", "deploy até 17/03")

**Heuristic:** Structural decisions define patterns that apply beyond a single project or time period. Operational decisions are execution choices tied to specific deliverables or dates. When ambiguous, default to `estrutural` (safer — keeps the decision visible longer).

## Edge Cases

- **Major org change**: If o gestor mentions a significant change (layoff, restructure, new leadership), escalate: conduct comprehensive refresh covering ALL files, not just flagged ones. Ask o gestor to walk through each affected area.
- **O gestor doesn't know details**: "Sem problema. Vou marcar em `context/pendings.md` e te lembro depois." Don't block the workflow — skip that item and continue.
- **Conflicting info between sources**: Default hierarchy: (1) the owner's word > (2) Most recent Slack/email > (3) ClickUp > (4) Vault. Always note the conflict in the report.
- **No divergences found**: "Vault está consistente com as fontes externas. Vou focar nos gaps de qualidade e profundidade."
- **MCP degradation**: If any external source fails, degrade gracefully with note. Continue with available sources — local vault audit is always valid.
- **Very large number of findings (20+)**: Group by priority and present top 10 first. Ask: "Tem mais [N] achados de menor prioridade. Quer ver ou posso aplicar as correções óbvias?"
- **Nothing to do**: If vault is fully consistent, complete, and fresh: "O vault está em ótimo estado! Nenhuma ação necessária. Próxima maintenance sugerida: [date]."
- **Você wants to abort mid-refresh**: "Sem problema. Vou salvar o que fizemos até agora e registrar os gaps restantes em pendings.md."
- **New entity discovered during refresh**: Create file following templates. If external person/company: use WebSearch for enrichment before creating.
- **Context compaction mid-workflow**: TaskList-based recovery — resume from first non-completed task.
- **Decisions.md very large (50+ entries)**: Prioritize archive evaluation. Flag to o gestor: "context/decisions.md tem [N] entradas. Archivei [X] operacionais. Quer revisar as estruturais também?"

## Quality Rules

- **Cross-reference is mandatory**: NEVER skip external source queries unless MCP is genuinely unavailable. The entire value of V2 maintenance is the vault↔external comparison.
- **Deduplication is mandatory**: NEVER write info that already exists in the destination file. Check before writing.
- **Decisions follow existing format**: Same table structure, increment row number (next after highest existing), include Tipo column.
- **New files follow templates**: `templates/person.md`, `templates/project-context.md`, `templates/company.md`.
- **Vault Health Score must be honest**: Don't inflate scores. If a dimension is 🔴, report it — the goal is awareness, not comfort.
- **Proactive depth requests**: Don't just check boxes — actively seek to make the vault richer. If a profile is shallow, ASK for more info. O gestor wants this.
- **Auto-corrections must be unambiguous**: Only auto-correct when the external source is clearly authoritative and there's no room for interpretation. When in doubt, ask.
- **Archive logic is deterministic**: No judgment calls on archiving. If conditions are met, archive. If not, don't. Never archive `estrutural` decisions.
- **Frontmatter consistency**: All files MUST have valid YAML frontmatter per conventions.md. Bump `last_updated` on every edit.
- **Task granularity**: Create ONE task per checklist item. Sub-tasks for individual file updates are additional. Never bundle.

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- The owner's profile: `team/<owner-slug>/<Owner Name>.md`
- The owner's dev plan: `team/<owner-slug>/<Owner Name> dev-plan.md`
- Team context: `context/team.md`
- Company context: `context/company.md`
- Decisions: `context/decisions.md`
- Pendings: `context/pendings.md`
- Skills matrix: `team/skills-matrix.md`
- Conventions: `docs/reference/conventions.md`
- Integrations: `docs/reference/integrations.md`

If audit was completed but findings not yet presented, re-compile from cached data.
If guided refresh started but not completed, present remaining gaps only.
If updates applied but not validated, present summary for PAUSE 3.
