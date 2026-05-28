---
name: cos-session-sync
description: Distribui informacoes da sessao atual pelos arquivos relevantes do vault (profiles, projects, decisions, context)
user-invocable: true
effort: low
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent, WebSearch, WebFetch
---

Distribuir informações relevantes da sessão atual pelos arquivos do vault.

This skill is the single source of truth for this workflow.
All instructions, routing rules, edge cases, and quality gates are here.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped. Create sub-tasks dynamically as needed (e.g., one task per profile to update, one per decision to append).

**Pre-flight**
0. **Load config** — read `context/cos-config.md` for `owner` and `language`

**Phase 1 — Scan**
1. **Scan conversation** — identify all distributable information from current session
2. **Build propagation manifest** — categorize items by destination, deduplicate against existing files

**Phase 2 — Validate**
3. ⏸️ **PAUSE: Clarify new entities** — ONLY if new people/projects/companies need info from você. Skip if all items are updates to existing files

**Phase 3 — Execute** (parallel agents)
4. **Propagate: people** — create/update profiles (spawn agent if items exist)
5. **Propagate: projects** — create/update project context files (spawn agent if items exist)
6. **Propagate: context files** — decisions, team, company, pendings, skills, owner's profile/dev-plan (spawn agent if items exist)

**Phase 4 — Close**
7. 🔍 **Quality gate: propagation completeness** — verify all manifest items were written
8. **Wrap-up** — report everything saved and propagated

## Process

### Step 0 — Load config

Read `context/cos-config.md` for identity (`owner`, `language`). This skill is vault-only; no integration checks needed.

### Step 1 — Scan conversation

Scan the ENTIRE current conversation for distributable information. Look for:

- **Decisions made** (outside formal meetings) — strategy shifts, policy changes, ad-hoc choices
- **People info** — new people mentioned, role/context updates, personal discoveries
- **Project updates** — status changes, new risks, new context, new projects
- **Priorities/strategy shifts** — focus changes, reprioritization
- **Company/external entity info** — new companies, partnerships, org changes
- **Competency observations** — skill demonstrations, growth signals
- **Pendings** — things Claude needs from o gestor to operate
- **Team changes** — role assignments, reporting changes
- **Owner's management practice** — competency practiced or missed (for dev-plan)

**Do NOT include:**
- Information already written to vault during this session by another workflow (e.g., if process-1on1 already ran and saved its record, skip everything it wrote)
- Ephemeral conversation artifacts (greetings, clarifications about Claude's behavior, meta-discussion about tools/skills)
- Information already present in destination files (verified in Step 2)

### Step 2 — Build propagation manifest

For each item found, classify and map to destination:

| Category | Destination | Action |
|----------|-------------|--------|
| Person info (team member) | `team/<member>/<Name>.md` | Update Notas, personal sections |
| Person info (other EP) | `people/<Name>.md` | Update or create with `templates/person.md` |
| Person info (external) | `people/<Name>.md` | Create with template + WebSearch for context |
| Project update | `projects/<kebab>/<Display Name>.md` | Update status, risks, notes, decisions |
| New project | `projects/<kebab>/<Display Name>.md` | Create with `templates/project-context.md` |
| Decision | `context/decisions.md` | Append row (increment #, include Tipo) |
| Owner's priorities | `team/<owner-slug>/<Owner Name>.md` | Update relevant sections |
| Company info (EP) | `context/company.md` | Update relevant section |
| Company info (external) | `companies/<Name>.md` | Create with `templates/company.md` + WebSearch |
| Competency | Member profile frontmatter `skills:` block | Update level or add observation |
| Skills matrix | `team/skills-matrix.md` | Update Analysis if gaps/risks changed |
| Pending | `context/pendings.md` | Append item |
| Team change | `context/team.md` | Update member info |
| Owner's dev-plan | `team/<owner-slug>/<Owner Name> dev-plan.md` | Append to Situation Log if management practice observed |

**Deduplication check:** For each item, read the destination file and verify:
- **Already present** in destination? → Mark as `skip` (note reason)
- **More recent version** of existing info? → Mark as `update`
- **Genuinely new**? → Mark as `new`

Build manifest as internal structured list with: item description, category, destination file, action (new/update/skip), and details.

### Step 3 — ⏸️ PAUSE: Clarify new entities (CONDITIONAL)

**Skip this step entirely** if all manifest items are updates to existing files or skips.

**Only pause if** new entities need creation and information is missing. Use AskUserQuestion for each:

**New person without full context:**
```
Question: "Encontrei [nome] na conversa sem perfil no vault. Quem é?"
Options:
- "[Role guess] na {{COMPANY_NAME}}" (if context suggests)
- "Externo — preciso saber empresa/cargo"
- "Não é relevante, pular"
```

**New project without context:**
```
Question: "Projeto [X] mencionado sem context file. Criar?"
Options:
- "Sim, com os dados que temos"
- "Sim, mas preciso adicionar contexto"
- "Não criar agora"
```

**New company:**
```
Question: "[Empresa] mencionada pela primeira vez. Criar perfil?"
Options:
- "Sim, buscar info na web"
- "Sim, com dados mínimos"
- "Não criar"
```

Ask as many questions as needed — one per new entity. Batch up to 4 related questions per AskUserQuestion call.

### Step 4 — Propagate: people (parallel agent)

**Skip if no people items in manifest.**

Spawn agent (`model: "sonnet"`, `subagent_type: cos-vault-loader`) with complete instructions:

- Full list of people items to propagate (with action: new/update and all details)
- For **new profiles**:
  - Use `templates/person.md` for structure
  - If a `comms` or `tasks` MCP is configured (see `context/cos-config.md`), look up the member's IDs via it and record them in the profile frontmatter
  - For external people: use WebSearch to enrich (role, company, LinkedIn context)
  - Mark web-sourced info with `<!-- Source: web search YYYY-MM-DD -->`
- For **updates**:
  - Read current file first
  - Edit relevant sections (Notas, personal profile, etc.)
  - Bump `last_updated` in frontmatter
- **All files MUST have YAML frontmatter** per `docs/reference/conventions.md`
- **All person mentions use `[[Full Name]]` wikilinks**

### Step 5 — Propagate: projects (parallel agent)

**Skip if no project items in manifest.**

Spawn agent (`model: "sonnet"`, `subagent_type: cos-vault-loader`) with complete instructions:

- Full list of project items to propagate (with action: new/update and all details)
- For **new projects**:
  - Use `templates/project-context.md` for structure
  - Create `projects/<kebab>/` folder + `projects/<kebab>/<Display Name>.md`
  - Tag: `project/<kebab>` + `project/active`
  - For projects involving external tools/platforms: use WebSearch/WebFetch for documentation
- For **updates**:
  - Read current file first
  - Update: status, risks & blockers, notes, key decisions, participants
  - Add meeting/session entry if applicable
- **All files MUST have YAML frontmatter**
- **All project references use `[[Project Display Name]]` wikilinks**

### Step 6 — Propagate: context files (parallel agent)

**Skip if no context items in manifest.**

Spawn agent (`model: "sonnet"`, `subagent_type: cos-vault-loader`) with complete instructions and the full list of context updates:

- **Decisions** → append to `context/decisions.md`
  - Follow existing table format: `| # | Date | Decision | Context/Rationale | Impacted | Source Meeting | Tipo |`
  - Increment # from last row
  - Source: "Sessão [date]" or specific context
  - Tipo: `estrutural` (permanent patterns) or `operacional` (execution tied to dates). When ambiguous → `estrutural`
- **Team changes** → update `context/team.md` (member info, roles, assignments)
- **Company info** → update `context/company.md` (org structure, products, partnerships)
- **Pendings** → append to `context/pendings.md`
- **Skills** → update member profile frontmatter `skills:` block + `team/skills-matrix.md` Analysis section if gaps/risks changed
- **Owner's profile** → update `team/<owner-slug>/<Owner Name>.md` (priorities, strategy)
- **Owner's dev-plan** → append to `team/<owner-slug>/<Owner Name> dev-plan.md` Situation Log if management practice observed

**Agents 4, 5, and 6 run in parallel.** Main thread waits for all to complete before proceeding.

### Step 7 — 🔍 Quality gate: propagation completeness

After all agents return, verify ALL manifest items from Step 2 were handled:

□ Every `new` item was created in the correct location?
□ Every `update` item was edited with correct content?
□ Every `skip` item was confirmed as already existing (not silently dropped)?
□ Decisions follow existing table format (same columns, incremented #, Tipo column)?
□ New files have complete YAML frontmatter per `docs/reference/conventions.md`?
□ All person mentions use `[[Full Name]]` wikilinks?
□ All project references use `[[Project Display Name]]` wikilinks?
□ `last_updated` bumped on all edited profiles?
□ No duplicate information written (deduplication respected)?

If any item fails → fix before proceeding. Do NOT mark this step completed with failures.

### Step 8 — Wrap-up

Report in Portuguese:

```
Distribui X informações desta sessão:

**Criados:**
- [file] — [what was created]

**Atualizados:**
- [file] — [what changed]

**Decisões:**
- #N: [decision summary]

**Pulados (já existiam):**
- [item] — já presente em [file]

Nenhuma ação necessária da sua parte.
```

If nothing was distributed: "Nenhuma informação nova para distribuir nesta sessão."

## Edge Cases

- **Nothing to distribute**: Report "Nenhuma informação nova para distribuir nesta sessão." — mark all tasks as completed and close immediately
- **New entity discovered**: Create file following templates. AskUserQuestion for missing details (full name, role) if not obvious from context
- **Conflicting info**: Update with latest (current session is more recent than vault), note the change in wrap-up report
- **Context compaction**: If context was compacted during the session, operate on available context. Note in report: "Contexto compactado nesta sessão — sync parcial."
- **Decision without clear Tipo**: Default to `estrutural` when ambiguous
- **Large session** (10+ items): Group by category in the report for readability. Consider splitting agent prompts if too many items per category
- **Ran after another v2 workflow**: Skip everything already written by that workflow's propagation gate. Only sync items from conversation phases NOT covered by the other workflow (e.g., ad-hoc discussion after the workflow completed)

## Quality Rules

- **Deduplication is mandatory** — never write info that's already in the destination file. Read before writing
- **Decisions follow existing format** — same table structure, increment row number, include Tipo column (estrutural/operacional)
- **New files follow templates** — `templates/person.md`, `templates/project-context.md`, `templates/company.md`
- **NO approval gate for execution** — execute directly and report. AskUserQuestion only for missing info on new entities
- **Wikilinks always** — `[[Full Name]]` for people, `[[Project Display Name]]` for projects. Never use markdown links for internal vault references
- **YAML frontmatter on every file** — per `docs/reference/conventions.md`
- **Factual only** — propagate what was said/decided, not interpretations. Claude's analysis stays in conversation, not in vault files

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress. Resume from the first non-completed task.

Key files to re-read on recovery:
- Conventions: `docs/reference/conventions.md`
- Decisions: `context/decisions.md` (to get last # for incrementing)
- Pendings: `context/pendings.md`
- Team: `context/team.md`
- Owner's profile: `team/<owner-slug>/<Owner Name>.md`

If the propagation manifest was built but not executed, re-scan available conversation context and rebuild it.
