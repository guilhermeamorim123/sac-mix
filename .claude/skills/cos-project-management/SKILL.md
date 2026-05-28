---
name: cos-project-management
description: Cria ou evolui projetos no `tasks` MCP — brainstorm adaptativo, estruturacao em marcos/tasks, e analise proativa de saude de projetos
user-invocable: true
argument-hint: <project-name-or-action>
effort: medium
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TaskCreate, TaskUpdate, TaskList, AskUserQuestion, Agent
---

Criar ou evoluir projeto no `tasks` MCP com $ARGUMENTS.

This skill is the single source of truth for project management via the `tasks` MCP.
All instructions, field IDs, routing rules, quality gates, and edge cases are here.

IMPORTANT: NEVER create or modify anything via the `tasks` MCP without the owner's explicit approval.

## Checklist

You MUST create a task for each item and complete them in order. Tasks should be **granular** — every discrete action gets its own task so nothing is skipped.

**Pre-flight**
0. **Load config + integration availability** — read cos-config.md, resolve tokens, check `tasks` capability

### Mode Detection

Detect mode from `$ARGUMENTS` and the owner's message:
- **Creation signals**: "criar projeto", "novo projeto", "quero estruturar X", project name not found via the `tasks` MCP
- **Evolution signals**: "adicionar marco", "atualizar", "mudar status", "corrigir rota", existing project name + alteration verb
- **Ambiguous**: Ask — "Quer criar um projeto novo ou evoluir um existente?"

---

### Creation Mode

**Phase 1 — Detection & Context**
1. **Detect creation mode** — parse $ARGUMENTS and the owner's message
2. **Pre-fill known context** — capture setor, solicitante, team member if mentioned

**Phase 2 — Adaptive Brainstorm**
3. **Assess clarity level** — clear vision (2-3 questions) vs vague idea (5-8 questions)
4. ⏸️ **Collect core information** — AskUserQuestion: objetivo, As-Is, To-Be, assignees, dependencies, risks
5. ⏸️ **Collect custom fields** — AskUserQuestion: solicitante, setor, complexidade, trimestre, valor, visibilidade
6. ⏸️ **Collect timeline per milestone** — AskUserQuestion: deadline for each proposed marco

**Phase 3 — Structure Proposal**
7. **Build project structure** — name, description, marcos, tasks, assignees, tags
8. ⏸️ **PAUSE: Present structure for approval** — AskUserQuestion with full structure preview

**Phase 4 — Quality Gate 1**
9. 🔍 **Pre-creation validation** — required fields, acceptance criteria, numbering, assignees

**Phase 5 — tasks execution (Steps 10-14)**
10. **Validate assignees** — resolve_assignees
11. **Create project task** — in list <projetos list id from tasks MCP details>, task_type "Projeto"
12. **Create [Revisão Técnica]** — conditional, only if tech/dev project
13. **Create marcos** — sequential, task_type "Milestone", one sub-task per marco
14. **Create tasks** — sequential per marco, one sub-task per task

**Phase 6 — Quality Gate 2**
15. 🔍 **Post-execution verification** — count, hierarchy, custom fields, URL

**Phase 7 — Propagation**
16. 🔍 **Build propagation manifest** — people, projects, decisions, context
17. **Execute propagation** — parallel agents if 2+ categories
18. 🔍 **Propagation completeness gate** — deduplication, frontmatter, wikilinks

**Phase 8 — Source Task & Notifications**
19. **Update source solicitação** — conditional: if project originated from a task in list Solicitações, update its status to "solução proposta" and link to project
20. **Notify stakeholders via the `comms` MCP** — DM assignee with full context + DM solicitante with summary

---

### Evolution Mode

**Phase 1 — Detection & Identification**
1. **Detect evolution mode** — parse $ARGUMENTS and the owner's message
2. **Identify target project** — search via the `tasks` MCP, disambiguate if needed

**Phase 2 — Conditional Read**
3. **Read project state** — conditional: full read for structural changes, skip for direct operations

**Phase 3 — Proactive Analysis**
4. **Analyze and signal health issues** — overdue, unassigned, missing fields, status misalignment

**Phase 4 — Proposal**
5. **Build change proposal** — additions, status changes, route corrections
6. ⏸️ **PAUSE: Present proposal for approval** — AskUserQuestion with before/after

**Phase 5 — Execution**
7. **Execute changes via MCP** — create/update tasks, delta only
8. 🔍 **Verify execution** — all changes applied, hierarchy intact

**Phase 6 — Propagation**
9. 🔍 **Build propagation manifest** — projects, decisions, context
10. **Execute propagation** — inline or parallel agents
11. 🔍 **Propagation completeness gate** — deduplication, wikilinks

## Process

> Se a capability `tasks` não estiver configurada, toda criação/atualização de task acontece como checkbox Obsidian Tasks na nota do projeto em `projects/`. Veja `docs/reference/obsidian-tasks.md` para a sintaxe.

### Step 0 — Load config + integration availability

Read `context/cos-config.md` and apply the **Config Contract** (`docs/reference/config-contract.md`).

This skill uses integrations: **clickup** (plus always-on vault).

- Read the "tasks" MCP details from `context/cos-config.md` and pass them to `cos-mcp-loader` (alongside the role name and `mcp`).
- If capability `tasks` is not configured → this skill manages projects **vault-only**: create/update the project context file in `projects/` and track tasks as Obsidian-Tasks checkboxes in the project note. Use the convention in `docs/reference/obsidian-tasks.md`: tasks are `- [ ]` checkboxes with `📅 due` under a `## Tarefas` section in the project note.
- If `true` → test the tasks MCP; if unavailable, warn and fall back to vault-only for this run.
- If `cos-config.md` is unpopulated, tell the user to run `/cos-setup`, then proceed vault-only.

### Mode Detection

1. If `$ARGUMENTS` contains a creation signal ("criar", "novo", "estruturar") → **Creation Mode**
2. If `$ARGUMENTS` contains an evolution signal ("adicionar", "atualizar", "status", "corrigir", "evoluir") → **Evolution Mode**
3. If `$ARGUMENTS` is a project name only:
   - Search via the `tasks` MCP via `filter_tasks` (list_ids: ["<projetos list id from tasks MCP details>"], subtasks: false), then scan results for matching project name
   - If found → **Evolution Mode**
   - If not found → **Creation Mode**
4. If ambiguous → AskUserQuestion: "Quer criar um projeto novo ou evoluir um existente?"
   - Options: "Criar novo" / "Evoluir existente: {project name}"

### Creation Mode

#### Phase 1 — Detection & Context

**Step 1 — Detect creation mode**
Mode already detected via Mode Detection above.

**Step 2 — Pre-fill known context**
Scan the owner's message for any pre-fillable data:
- If the owner mentions a setor → note it for custom fields
- If the owner mentions a person as solicitante → note name + email
- If the owner mentions team members → note for assignees
- If the owner mentions a deadline → note for timeline

#### Phase 2 — Adaptive Brainstorm

**Step 3 — Assess clarity level**

Evaluate the owner's message against these criteria:
- **Clear vision** = the owner describes problem + solution + scope (at least 2 of 3). Example: "Quero criar um sistema de mentorias com módulo de agendamento e acompanhamento"
- **Vague idea** = the owner describes only a general need. Example: "Preciso resolver o problema das mentorias"

If clear → proceed with 2-3 validation questions (confirm scope, identify gaps)
If vague → proceed with 5-8 discovery questions (problem root, users, scope, dependencies, risks)

**Step 4 — Collect core information**

Use AskUserQuestion to collect. Adapt questions to clarity level.

For **vague ideas**, start with:

⏸️ AskUserQuestion:
"Vou te ajudar a estruturar esse projeto. Primeira pergunta:"

Question 1: "Qual o problema que esse projeto resolve? O que acontece hoje que não deveria acontecer?"
(open text)

Then follow up based on answer:
Question 2: "Quem são os usuários/beneficiários diretos?"
Options: list team members + setores + "Externo" + "Outro"

Question 3: "Já existe alguma solução parcial hoje (planilha, processo manual, sistema)?"
Options: "Sim, [descrever]" / "Não, é do zero" / "Tem algo mas não funciona"

Question 4: "Quais as dependências externas? (APIs, aprovações, outros times)"
(open text)

Question 5: "Quais os riscos que você já enxerga?"
(open text)

For **clear visions**, validate with:

⏸️ AskUserQuestion:
"Entendi a visão. Vou validar alguns pontos:"

Question 1: "O escopo inclui [X, Y, Z] — falta algo ou tem algo a mais?"
(based on what você descreveu)

Question 2: "Dependências externas ou riscos que eu preciso saber?"
(open text)

From the collected answers, derive:
- Objetivo do projeto (1-2 sentences)
- Situação atual (As-Is)
- Situação futura (To-Be)
- Assignees
- Dependencies
- Risks

**Step 5 — Collect custom fields**

⏸️ AskUserQuestion:
"Agora os campos do projeto no `tasks` MCP:"

Question 1: "Quem é o solicitante desse projeto?"
Options: list names from context + "Outro"

Question 2: "Qual o setor?"
Options: os setores da sua empresa (ex: "Comercial" / "Financeiro" / "Marketing" / "Operações" / "Recursos Humanos" / "TI" / "Outro"). Ajuste à estrutura da sua empresa em `context/company.md`.

Question 3: "Complexidade estimada?"
Options: "Baixa (< 8h)" / "Média (8-40h)" / "Alta (40-120h)" / "Muito Alta (> 120h)"

Then suggest and confirm:
- Trimestre: suggest based on scope/deadline
- Valor de negócio: suggest based on context (quick-win, estrategico, inovacao, etc.)
- Visibilidade: suggest based on context (demo, case-sucesso, documentar, etc.)

"Sugiro: Trimestre Q2 2026, valor 'estrategico', visibilidade 'documentar'. Concorda ou quer ajustar?"

**Step 6 — Collect timeline per milestone**

After proposing the marcos (in step 7), ask o gestor for deadlines:

⏸️ AskUserQuestion (one question per marco):
"Prazo para o Marco {N}: {título}?"
Options: "Esta semana" / "Próxima semana" / "2 semanas" / "1 mês" / "Definir data: [dd/mm]"

Convert the answer to absolute date (based on today's date).

#### Phase 3 — Structure Proposal

**Step 7 — Build project structure**

Using all collected information, build the complete structure:

**Project name:** `{Nome} — {Subtítulo descritivo}`
Example: `{{PROJECT_NAME}} — Plataforma de gestão e acompanhamento`

**Description:** Use this template (markdown_description parameter):
```
## Visão geral
{Parágrafo contextual — 2-3 sentences}

**Setor:** {setor}
**Solicitante:** {nome} ({setor}) — {email}
{**Integração técnica:** {nome} — {contexto} — only if applicable}

## O que é
{Bullets descrevendo o que o projeto faz/entrega}

## Stack técnico
{Ferramentas, APIs, plataformas — only if applicable}

## Fases
| Marco | Descrição | Tasks | Deadline |
|-------|-----------|-------|----------|
| 0 | {título} | {N} | {dd/mm} |
| 1 | {título} | {N} | {dd/mm} |

## Referências
{Decision #N: descrição}
```

**Marcos:** Number from 0 (infra/setup) or 1 (no setup needed). Pattern: `Marco {N}: {Título}`

**Tasks:** Number as `{marco}.{seq}`. Pattern: `{N}.{M} {Título}`

**Assignees:** Route based on each team member's specialty, read from `team/<slug>/<Name>.md` (`clickup_id` + specialties in frontmatter):
- Owner (<your user id from tasks MCP details>): architecture, complex work, strategic
- Each team member (`<clickup_id from profile>`): route by the specialty listed in their profile
- If unclear, ask Owner

**Tags:** Suggest based on context:
- `automação` if involves automation/integration
- `novo` if new product/system
- `terceiros` if depends on external partner
- `alto-risco` if may impact other systems
- `experimental` if high uncertainty

**[Revisão Técnica]:** Include ONLY if project involves technology/development (code, APIs, systems). Do NOT include for documentation, process mapping, or presentation projects.

**Step 8 — PAUSE: Present structure for approval**

⏸️ Present the complete structure to o gestor:

```
📋 **Estrutura proposta: "{Nome do Projeto}"**

**Projeto:** {nome completo}
**Setor:** {setor} | **Complexidade:** {complexidade} | **Trimestre:** {trimestre}
**Solicitante:** {nome} ({email})
**Assignees:** {nomes}
**Tags:** {tags}
**Valor:** {valor de negocio} | **Visibilidade:** {visibilidade}

**Marcos e Tasks:**

Marco 0: {título} — deadline: {dd/mm}
  0.1 {task} → {assignee}
  0.2 {task} → {assignee}

Marco 1: {título} — deadline: {dd/mm}
  1.1 {task} → {assignee}
  1.2 {task} → {assignee}
  1.3 {task} → {assignee}

[Revisão Técnica] → revisor técnico do time (se aplicável)

**Custom Fields:**
- Objetivo: {texto}
- Situação Atual: {texto}
- Situação Futura: {texto}
- Riscos: {texto}
```

AskUserQuestion:
"Essa estrutura bate? Quer ajustar algo antes de criar no `tasks` MCP?"
Options: "Pode criar" / "Preciso ajustar" / "Refazer do zero"

**WAIT.** Do NOT proceed until você responds.
- If "Pode criar" → proceed to Phase 4
- If "Preciso ajustar" → ask what to change, apply, re-present
- If "Refazer" → return to Phase 2

#### Phase 4 — Quality Gate 1: Pre-Creation

**Step 9 — Validate before creating**

🔍 **Quality gate: Pre-Creation**

- [ ] All required custom fields have values: solicitante, email, setor, complexidade, objetivo
- [ ] Every marco has critérios de aceite defined (text, not empty)
- [ ] Every marco has deadline confirmed by o gestor
- [ ] Sequential numbering without gaps (marcos: 0,1,2... or 1,2,3...; tasks: N.1, N.2...)
- [ ] Description follows the markdown template from Step 7
- [ ] Assignees are valid team member IDs (verified against Data Reference)
- [ ] The owner explicitly approved the structure in Step 8

If any item fails → fix before proceeding. Do NOT mark this step completed with failures.

#### Phase 5 — tasks execution (Only if capability `tasks` is configured)

**Step 10 — Validate assignees** (Only if capability `tasks` is configured)

Call `resolve_assignees` with all proposed assignee names/emails to confirm they resolve to valid IDs. If any fail, ask o gestor for clarification.

**Step 11 — Create project task** (Only if capability `tasks` is configured)

Call `create_task` with:
```
name: "{Nome} — {Subtítulo}"
list_id: "<projetos list id from tasks MCP details>"
task_type: "Projeto"
markdown_description: <full markdown from Step 7 template>
status: "planejamento"
priority: "high" (or as determined)
assignees: [<user IDs from resolve step>]
tags: [<selected tags>]
custom_fields: [
  { "id": "<cf: Solicitante>", "value": [<solicitante user ID>] },
  { "id": "<cf: E-mail do solicitante>", "value": "<email>" },
  { "id": "<cf: Setor>", "value": "<setor option ID>" },
  { "id": "<cf: Complexidade>", "value": "<complexidade option ID>" },
  { "id": "<cf: Objetivo do Projeto>", "value": "<objetivo text>" },
  { "id": "<cf: Situação Atual>", "value": "<situacao atual text>" },
  { "id": "<cf: Situação Futura>", "value": "<situacao futura text>" },
  { "id": "<cf: Impacto em Produtividade>", "value": "<impacto text>" },
  { "id": "<cf: Riscos Identificados>", "value": "<riscos text>" },
  { "id": "<cf: Trimestre de Entrega>", "value": "<trimestre option ID>" },
  { "id": "<cf: Valor de Negócio>", "value": [<valor de negocio label IDs>] },
  { "id": "<cf: Visibilidade>", "value": [<visibilidade label IDs>] }
]
```

**Format rules:**
- Dropdown fields (setor, complexidade, trimestre): `"value": "<single option ID string>"`
- Label fields (valor de negocio, visibilidade): `"value": ["<id1>", "<id2>"]` (array)
- Text fields: `"value": "<text string>"`
- Email fields: `"value": "<email string>"`
- Users fields (solicitante): `"value": [<integer user ID>]` (array of ints)

Omit any optional field that has no value (don't send empty strings).

Save the returned task ID as `PROJECT_ID`.

**Step 12 — Create [Revisão Técnica] (conditional)** (Only if capability `tasks` is configured)

**Only if** the project involves technology/development (code, APIs, systems, integrations, automations). Do NOT create for documentation-only, process mapping, or presentation projects.

If applicable, call `create_task`:
```
name: "[Revisão Técnica] {Project Name}"
parent: "<PROJECT_ID>"
assignees: ["<tech reviewer clickup_id from profile>"]
priority: "high"
status: "em revisão"
```
Then call `add_tag_to_task`:
```
task_id: "<revisao_tecnica_task_id>"
tag_name: "revisao-tecnica"
```

**Step 13 — Create marcos (sequential)** (Only if capability `tasks` is configured)

For each marco in the approved structure, call `create_task`:
```
name: "Marco {N}: {Título}"
parent: "<PROJECT_ID>"
task_type: "Milestone"
priority: "high"
assignees: [<marco assignee IDs>]
due_date: "<YYYY-MM-DD>"
status: "planejamento"
custom_fields: [
  { "id": "<cf: Critérios de Aceite>", "value": "<critérios de aceite text>" },
  { "id": "<cf: Entregáveis>", "value": "<entregáveis text>" }
]
```

Save each returned task ID as `MARCO_{N}_ID`.
Create marcos in sequential order (Marco 0, 1, 2...) to maintain correct ordering via the `tasks` MCP.

**Step 14 — Create tasks (sequential per marco)** (Only if capability `tasks` is configured)

For each task in each marco, call `create_task`:
```
name: "{N}.{M} {Título}"
parent: "<MARCO_{N}_ID>"
assignees: [<task assignee IDs>]
due_date: "<YYYY-MM-DD>" (optional — inherit marco deadline if not specified)
time_estimate: "<minutes>" (optional)
status: "pendente"
```

Create tasks in sequential order within each marco to maintain correct ordering.
Tasks use the default task type (omit task_type parameter).
Do NOT apply project-level or marco-level custom fields to tasks.

#### Phase 6 — Quality Gate 2: Post-Execution

**Step 15 — Verify creation**

🔍 **Quality gate: Post-Execution**

- [ ] All marcos created (count matches approved structure)
- [ ] All tasks created under correct marcos (parent IDs verified)
- [ ] Custom fields applied on project (spot-check 2-3 fields via `get_task`)
- [ ] Custom fields applied on marcos (critérios de aceite present)
- [ ] Hierarchy correct (tasks → marcos → project)
- [ ] Project URL accessible: report `https://app.clickup.com/t/<PROJECT_ID>` to o gestor

If any item fails → retry the failed creation/update calls. Report final state to o gestor.

#### Phase 7 — Universal Propagation Gate

**Step 16 — Build propagation manifest**

Scan the session for new/updated information. Classify into categories:

- **PEOPLE**: New stakeholders mentioned during brainstorm (not already in `people/` or `team/`)
- **PROJECTS**: New project context file needed in `projects/<slug>/`
- **DECISIONS**: If project creation itself was a decision (e.g., agreed in a meeting), append to `context/decisions.md`
- **CONTEXT**: Update `context/pendings.md` if blockers/dependencies exist

**Slug derivation:** Before creating a project folder, run `ls projects/` to check for an existing folder with a matching or similar name. Use the existing folder name if found. Only derive a new kebab-case slug if no match exists.

**Step 17 — Execute propagation**

If 2+ categories have items → spawn parallel agents using `cos-vault-loader`:
- **Projects Agent** (`subagent_type: cos-vault-loader`): create project context file using `templates/project-context.md`, include task link and marcos summary
- **Context Agent** (`subagent_type: cos-vault-loader`): update context/decisions.md, pendings.md

If only 1 category → execute inline (no subagent).

**Step 18 — Propagation completeness gate**

🔍 **Quality gate: Propagation Completeness**

- [ ] All manifest items executed
- [ ] No duplicate decisions written (check existing entries before appending)
- [ ] Frontmatter complete on new files (per `docs/reference/conventions.md`)
- [ ] Wikilinks correct (`[[Full Name]]` for people, `[[Project Name]]` for projects)

If any item fails → fix before marking complete.

#### Phase 8 — Source Task & Notifications

**Step 19 — Update source solicitação (conditional)** (Only if capability `tasks` is configured)

If the project originated from a task in the **Solicitações** list (list ID: `<solicitações list id from tasks MCP details>`):
1. Update the source task status to `solução proposta` via `update_task`
2. Link the source task to the project via `clickup_add_task_link(task_id: "<source_task_id>", links_to: "<PROJECT_ID>")`

**Detection:** Check if the owner's message references a task URL or ID from the Solicitações list. If the task's `list.id` is `<solicitações list id from tasks MCP details>`, it's a solicitação.

If the project does NOT originate from a solicitação → skip this step.

**Step 20 — Notify stakeholders via the `comms` MCP**

Send comms DMs to the key stakeholders. Use `send_message` (never drafts — per feedback rules).

**To the assignee (person executing the project):**
Include:
- Project name and task link
- Brief context of what the project is about
- Summary of marcos and deadlines
- Key dependencies or pre-start actions (e.g., questions to resolve with solicitante)
- Who to contact for requirements clarification
- Link to source document/task if applicable

**To the solicitante (person who requested):**
Include:
- Project name and task link
- Who will lead the execution
- That the assignee will reach out for pending questions
- Expected go-live date
- Link to the source solicitação task

**comms ID lookup:** Read the person's profile file in `team/<member>/` or `people/<Name>.md` — the `slack_id` is in the YAML frontmatter. If not found, use `search_users` via MCP.

### Evolution Mode

#### Phase 1 — Detection & Identification

**Step 1 — Detect evolution mode**
Mode already detected via Mode Detection above.

**Step 2 — Identify target project**

1. Extract project name from `$ARGUMENTS` or the owner's message
2. Search via the `tasks` MCP: `filter_tasks(list_ids: ["<projetos list id from tasks MCP details>"], subtasks: false)`
3. Scan results for matching project name (case-insensitive partial match)
4. If **one match** → proceed with that project
5. If **multiple matches** → AskUserQuestion: "Encontrei vários projetos similares:" + list options
6. If **no match** → AskUserQuestion: "Projeto '{name}' não encontrado. Quer criar um novo?"
   - Options: "Criar novo" / "Buscar com outro nome" / "Cancelar"

#### Phase 2 — Conditional Read

**Step 3 — Read project state (conditional)**

Classify the operation:
- **Needs context** (add marco, correct route, restructure, health check): read full project
- **Direct operation** (change status, update deadline, update single field): skip read, go to Phase 4

If needs context:
1. Call `get_task(task_id: "<project_id>", subtasks: true, detail_level: "summary")`
2. If response is truncated or too large → spawn an agent (`subagent_type: cos-mcp-loader`) to read incrementally:
   - Agent reads marcos via `filter_tasks` with parent filter
   - Agent reads tasks per marco
   - Agent returns consolidated state summary
3. Build and present state summary to o gestor:
   ```
   📊 Estado atual: "{Nome do Projeto}"
   Status: {status} | Marcos: {N total} ({N concluídos}/{N em andamento}/{N pendentes})

   Marco 0: {título} — {status} — {N tasks concluídas}/{N total}
   Marco 1: {título} — {status} — {N tasks concluídas}/{N total}
   ...
   ```

#### Phase 3 — Proactive Analysis

**Step 4 — Analyze and signal health issues**

When project state was read in step 3, automatically check for:

| Check | Condition | Signal |
|-------|-----------|--------|
| Overdue marco | due_date < today AND status != "concluído" | ⚠️ Marco {N} atrasado desde {dd/mm} |
| Unassigned tasks | task.assignees is empty | ⚠️ {N} tasks sem responsável |
| Missing acceptance criteria | marco custom_field "887e7d8c..." is empty | ⚠️ Marco {N} sem critérios de aceite |
| Empty required fields | project missing solicitante/setor/complexidade/objetivo | ⚠️ Campo '{field}' vazio no projeto |
| Numbering gaps | marco/task names don't follow sequential pattern | ⚠️ Numeração inconsistente |
| Status misalignment | marco "em andamento" but all children "pendente" | ⚠️ Status desalinhado no Marco {N} |

If issues found, present before proceeding:
```
**Observações antes de prosseguir:**

⚠️ Marco 2 atrasado desde 15/03 — Sugiro: atualizar deadline ou marcar como bloqueado
⚠️ 3 tasks sem responsável no Marco 1 — Sugiro: atribuir ao {membro}
⚠️ Campo 'Objetivo' vazio no projeto — Sugiro: preencher com "{texto}"

"Quer corrigir essas observações agora ou seguir com a alteração que pediu?"
Options: "Corrigir agora" / "Ignorar, seguir com o pedido" / "Corrigir depois"
```

If no issues found, proceed silently to Phase 4.

#### Phase 4 — Proposal

**Step 5 — Build change proposal**

Based on the owner's request, build the proposal:

- **Add marcos/tasks**: Propose with sequential numbering continuing from last existing (e.g., if last is Marco 3, new is Marco 4). Include deadlines (ask o gestor), assignees, critérios de aceite for marcos.
- **Update status/deadline**: Show current → proposed (e.g., "Marco 2: planejamento → em andamento")
- **Correct route**: Present current state vs restructured proposal
- **Update description/fields**: Show diff of what changes

**Step 6 — PAUSE: Present proposal for approval**

⏸️ Present the change proposal:

```
📝 **Alteração proposta em "{Nome do Projeto}":**

{For additions:}
**Novos marcos/tasks:**
Marco 4: {título} — deadline: {dd/mm}
  4.1 {task} → {assignee}
  4.2 {task} → {assignee}

{For status changes:}
**Mudanças de status:**
- Marco 2: planejamento → em andamento
- Task 1.3: pendente → concluído

{For field updates:}
**Campos atualizados:**
- Complexidade: Média → Alta
- Trimestre: Q1 → Q2 2026

{For route corrections:}
**Reestruturação:**
- Marco 3 (original): dividido em Marco 3A e 3B
- Tasks 3.1-3.3 → Marco 3A
- Tasks 3.4-3.6 → Marco 3B (novo)
```

AskUserQuestion:
"Confirma essa alteração?"
Options: "Confirma" / "Ajustar" / "Cancelar"

**WAIT.** Do NOT proceed until você responds.
- If "Confirma" → proceed to Phase 5
- If "Ajustar" → ask what to change, rebuild proposal, re-present
- If "Cancelar" → stop workflow

#### Phase 5 — Execution

**Step 7 — Execute changes via MCP** (Only if capability `tasks` is configured)

Apply changes using delta-only calls:
- New marcos: `create_task` with `task_type: "Milestone"`, `parent: "<project_id>"`, custom_fields
- New tasks: `create_task` with `parent: "<marco_id>"`
- Status updates: `update_task(task_id: "<id>", status: "<new_status>")`
- Field updates: `update_task(task_id: "<id>", custom_fields: [{...}])`
- Deadline updates: `update_task(task_id: "<id>", due_date: "<YYYY-MM-DD>")`
- Tag changes: `add_tag_to_task` / `clickup_remove_tag_from_task`

If the project structure changed (new marcos, renamed marcos), also update the project description (fases table) via `update_task(task_id: "<project_id>", markdown_description: "<updated>")`.

**Step 8 — Verify execution**

🔍 **Quality gate: Execution Verification**

- [ ] All proposed additions created successfully
- [ ] All proposed updates applied (spot-check via `get_task`)
- [ ] Hierarchy intact (no orphaned tasks)
- [ ] No unintended side-effects

If any item fails → retry failed call. Report final state to o gestor.

#### Phase 6 — Universal Propagation Gate

**Step 9 — Build propagation manifest**

Scan session for changes that need vault propagation:
- **PROJECTS**: Update project context file if significant changes (new marcos, route correction, scope change)
- **DECISIONS**: Append to `context/decisions.md` if route correction was a decision
- **CONTEXT**: Update `context/pendings.md` if new blockers/dependencies surfaced

**Slug derivation:** Run `ls projects/` to find existing project folder. Use exact existing name.

**Step 10 — Execute propagation**

If 2+ categories → spawn parallel agents using `cos-vault-loader`. If 1 category → execute inline.

**Step 11 — Propagation completeness gate**

🔍 **Quality gate: Propagation Completeness**

- [ ] All manifest items executed
- [ ] No duplicate decisions
- [ ] Wikilinks correct in all written files

## Edge Cases

- **Ambiguous mode**: Ask o gestor explicitly
- **Project not found in evolution mode**: "Projeto '{name}' não encontrado. Quer criar um novo?"
- **Multiple projects match**: Present list, ask o gestor to pick
- **Large project response truncated**: Spawn agent (`subagent_type: cos-mcp-loader`) to read incrementally
- **The owner rejects structure in PAUSE**: Collect feedback, rebuild, re-present
- **No tech/dev in project**: Skip [Revisão Técnica] entirely
- **The owner provides partial info**: Fill what's available, ask for rest — don't guess
- **Solicitante is external (not via the `tasks` MCP)**: Use the owner's ID as fallback, note in description
- **Marco without tasks**: Allowed (placeholder marco for future planning)

## Recovery

If context was compacted mid-workflow, run TaskList to determine current progress.

**If compacted during brainstorm** (before any task creation):
- Present: "Perdi o contexto do brainstorm. Pode resumir o que combinamos, ou quer recomeçar?"
- If você provides summary, rebuild proposal and proceed to approval

**If compacted during tasks execution** (some items created):
- Read project from the `tasks` MCP: `get_task` with `subtasks: true`
- Compare against proposal to identify remaining items
- Resume from first non-created item

**If compacted during evolution:**
- Re-read project state from the `tasks` MCP
- Check which proposed changes were already applied
- Resume from first non-applied change

Key files to re-read on recovery:
- This SKILL.md (Data Reference section — all field IDs, routing rules, and statuses are here)
- The project's vault context file if it exists

## Data Reference

### Task List

| List | ID |
|------|----|
| Projetos | `<projetos list id from tasks MCP details>` |
| Solicitações | `<solicitações list id from tasks MCP details>` |

### Custom Fields — Project Level

> **IDs são workspace-specific.** Os custom fields abaixo são uma estrutura recomendada de projeto. Para obter os IDs reais do seu MCP de `tasks`, rode `clickup_get_custom_fields` na sua lista de Projetos uma vez e mapeie por nome (a skill referencia os campos por nome como `<cf: Nome>`). Crie no seu MCP de `tasks` os campos que não existirem.

| Field | Type | When to fill |
|-------|------|-------------|
| Solicitante | users | Always (required) |
| E-mail do solicitante | email | Always (required) |
| Setor | dropdown | Always (required) |
| Complexidade | dropdown | Always (required) |
| Objetivo do Projeto | text | Always (required) |
| Situação Atual - As Is | text | When available |
| Situação Futura - To Be | text | When available |
| Impacto em Produtividade | text | When identified |
| Riscos Identificados | text | When identified |
| Trimestre de Entrega | dropdown | Suggest to o gestor |
| Valor de Negócio | labels | Suggest to o gestor |
| Visibilidade/Apresentação | labels | Suggest to o gestor |

**Fields to IGNORE** (workspace-level, auto-fill, or irrelevant):
- Canal, Formato, Parceiro, Categoria de Tarefa (AI auto-categorized), Progresso (auto-calculated), Perfil, Anexos

### Custom Fields — Marco Level

| Field | Type | When to fill |
|-------|------|-------------|
| Critérios de Aceite | text | Always (required) |
| Entregáveis | text | When defined |

Do NOT apply project-level custom fields to marcos or tasks.

### Custom Fields — Task Level

No custom fields. Use only native task fields:
- `name`, `assignees`, `due_date`, `time_estimate`, `markdown_description`

### Dropdown / Label Option IDs

> **Option IDs são workspace-specific.** Rode `clickup_get_custom_fields` na sua lista de Projetos para obter os IDs das opções de cada campo dropdown/label e mapeie por nome. Os valores abaixo são vocabulários sugeridos (sem IDs); adapte aos da sua empresa.

- **Setor** (dropdown): os setores da sua empresa (ver `context/company.md`).
- **Complexidade** (dropdown): `Baixa (< 8h)` / `Média (8-40h)` / `Alta (40-120h)` / `Muito Alta (> 120h)`.
- **Trimestre de Entrega** (dropdown): `Q1 2026`, `Q2 2026`, … (ajuste ao período).
- **Valor de Negócio** (labels): `quick-win`, `estrategico`, `inovacao`, `reducao-custo`, `revenue`, `cliente-externo`, `compliance`, `escalabilidade`, `padronização`.
- **Visibilidade** (labels): `demo`, `case-sucesso`, `documentar`, `portfolio`, `board-report`.

### Tags

| Tag | Use when |
|-----|----------|
| `automação` | Project involves automation/integration |
| `novo` | New product/system (not maintenance) |
| `terceiros` | Depends on external partner/vendor |
| `alto-risco` | May impact other systems |
| `sensivel` | Sensitive data, LGPD |
| `bloqueante` | Blocks other projects if delayed |
| `experimental` | High uncertainty, may fail |
| `comercial` | Commercial sector project |
| `revisao-tecnica` | Applied to `[Revisão Técnica]` tasks |

### Team Assignment Routing

Assignment is driven by each member's profile. Read `clickup_id` and specialties from `team/<slug>/<Name>.md`; route tasks to the member whose specialty matches the work.

| Member | tasks MCP ID | Assign for |
|--------|-----------|-----------|
| Owner | `<your user id from tasks MCP details>` | Strategic decisions, architecture, complex work |
| Each team member | `<clickup_id from their profile>` | Their specialty (see profile frontmatter) |

If assignee not clear from context, ask o gestor.

### Statuses

| Status | Meaning |
|--------|---------|
| `planejamento` | Initial state for projects and marcos |
| `em revisão` | Under technical review |
| `pendente` | Waiting for external dependency |
| `em andamento` | Active work |
| `bloqueado` | Blocked by issue |
| `em teste` | Testing/validation phase |
| `concluído` | Completed |
| `cancelado` | Cancelled |
| `finalizado` | Archived after completion |

### Statuses — Solicitações List (`<solicitações list id from tasks MCP details>`)

| Status | Type | Meaning |
|--------|------|---------|
| `pendente` | Not started | New request, not yet reviewed |
| `em andamento` | Active | Being analyzed/worked on |
| `solução proposta` | Done | Solution proposed — project created or response given |
| `cancelado` | Done | Request cancelled |
| `arquivado` | Closed | Archived after resolution |

### Custom Field Format Rules

| Field type | Format | Example |
|------------|--------|---------|
| dropdown | `"value": "<single option ID string>"` | `"value": "<option ID from clickup_get_custom_fields>"` |
| labels | `"value": ["<id1>", "<id2>"]` (array of strings) | `"value": ["<label ID 1>", "<label ID 2>"]` |
| text | `"value": "<text string>"` | `"value": "Automatizar processo de onboarding"` |
| email | `"value": "<email string>"` | `"value": "team.member@<your company email domain>"` |
| users | `"value": [<integer user ID>]` (array of ints) | `"value": [<your user id from tasks MCP details>]` |

Omit any optional field that has no value — do not send empty strings or empty arrays.

### Project Name Patterns

```
Project:  {Nome do Projeto} — {Subtítulo descritivo}
Marco:    Marco {N}: {Título}
Task:     {marco_number}.{task_seq} {Título}
```

Examples:
- `{{PROJECT_NAME}} (Comercial) — Agente IA de Vendas de Eventos via WhatsApp`
- `Marco 0: Infraestrutura & Setup`
- `1.1 Mapear endpoints da API`
