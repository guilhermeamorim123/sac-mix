# CoS Reference: Conventions

> Referenced by CLAUDE.md. Changes here must follow Structure Change Policy.
> Read this file when CLAUDE.md "Conventions" section directs you to.

---

### File Naming
- **Team member folders**: `kebab-case` (e.g., `maria-santos`)
- **Project folders**: `kebab-case` (e.g., `projeto-alpha`, `sistema-crm`)
- **People profiles (non-team)**: `people/` (flat, one `Full Name.md` per person)
- **Meeting folders**: `YYYY-MM-DD/` (inside `team/<member>/meetings/`, `weeklys/`, or `projects/<project>/meetings/` — including `projects/standalone-meetings/meetings/` for multi-project meetings)
- **Multiple same day**: `YYYY-MM-DD-2/`

**Files inside meeting folders:**

| Type | Name Pattern | Example |
|------|-------------|---------|
| 1:1 meeting | `YYYY-MM-DD 1on1 FirstName.md` | `2026-03-09 1on1 TeamMember.md` |
| 1:1 prep | `YYYY-MM-DD prep 1on1 FirstName.md` | `2026-03-09 prep 1on1 TeamMember.md` |
| Weekly meeting | `YYYY-MM-DD weekly.md` | `2026-03-09 weekly.md` |
| Weekly prep | `YYYY-MM-DD prep weekly.md` | `2026-03-09 prep weekly.md` |
| Project meeting | `YYYY-MM-DD project-kebab.md` | `2026-03-10 project-alpha.md` |
| Standalone meeting | `YYYY-MM-DD <category> <description>.md` | `2026-03-16 alinhamento stakeholder.md` |
| Transcription | `transcription.txt` | `transcription.txt` |
| Original audio | `original.<ext>` | `original.mp3` |

**Other files:**

| Type | Name Pattern | Location | Example |
|------|-------------|----------|---------|
| Member profile | `First Last.md` | `team/<member>/` | `Team Member.md` |
| Dev plan | `First Last dev-plan.md` | `team/<member>/` | `Team Member dev-plan.md` |
| Project context | `Project Display Name.md` | `projects/<project>/` | `{{PROJECT_NAME}}.md` |
| Daily brief | `YYYY-MM-DD.md` | `daily-briefs/` | `2026-03-11.md` |
| Person profile (non-team) | `Full Name.md` | `people/` | `Stakeholder Name.md` |
| Memory file | `<topic>.md` | `memory/` | `reference_partner-x.md` |
| Memory index | `MEMORY.md` | `memory/` | `MEMORY.md` |

### Obsidian Conventions

This vault is Obsidian-compatible. Claude generates all files via VS Code; the owner uses Obsidian as read-only viewer for navigation, graph view, and search.

#### YAML Frontmatter (MANDATORY on all generated .md files)

Every markdown file Claude creates MUST have YAML frontmatter. Schemas by type:

**Meetings (1:1, weekly, project):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `meeting` |
| subtype | string | Yes | `1on1`, `weekly`, `project`, or `standalone` |
| date | date | Yes | `YYYY-MM-DD` |
| participant | wikilink string | 1on1 only | `"[[Full Name]]"` |
| participants | list of wikilink strings | weekly/project | `- "[[Full Name]]"` |
| absent | list | weekly only | `[]` if none |
| project | wikilink string | project only | `"[[Project Name]]"` |
| status | string | Yes | `completed` |
| tags | list | Yes | See tag taxonomy |
| category | string | standalone only | `alinhamento`, `estrategica`, `ad-hoc`, `diretoria` |
| projects_discussed | list of wikilink strings | standalone only | `- "[[Project Name]]"` — all projects touched in this meeting |

**Preps (1:1 prep, weekly prep):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `prep` |
| subtype | string | Yes | `1on1` or `weekly` |
| date | date | Yes | `YYYY-MM-DD` |
| participant | wikilink string | 1on1 only | `"[[Full Name]]"` |
| tags | list | Yes | See tag taxonomy |

**Person profiles:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `person` |
| name | string | Yes | Full name |
| role | string | Yes | Job title |
| email | string | Yes | Corporate email |
| clickup_id | number | If known | ClickUp user ID |
| slack_id | string | If known | Slack member ID |
| status | string | Yes | `active` |
| sector | string | If known | Department/team |
| company | string | If known | "{{COMPANY_NAME}}" for internal, company name for external |
| first_seen | string | If known | First meeting/context where mentioned |
| aliases | list | Recommended | First name, nicknames — enables flexible wikilink resolution |
| skills | list of objects | Recommended | Skill levels by category. Structure: `[{category, items: [{name, level, target?}]}]`. Level 1-5 or null (pending). Target is optional — only for skills under active development. See Scale Definition in `skills-matrix.md` |
| tags | list | No | Optional — for ad-hoc categorization |

**Development plans:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `development-plan` |
| person | wikilink string | Yes | `"[[Full Name]]"` |
| last_updated | date | Yes | `YYYY-MM-DD` |
| tags | list | Yes | `development` |

**Project context:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `project` |
| name | string | Yes | Display name |
| status | string | Yes | `em andamento`, `concluído`, `planejamento` |
| owner | wikilink string | Yes | `"[[Owner Name]]"` |
| clickup_list | string | If applicable | ClickUp list ID |
| started | date | If known | `YYYY-MM-DD` |
| tags | list | Yes | `project/<kebab>`, `project/active` or `project/completed` |

**Context files (company, team, people, etc.):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `context` |
| subtype | string | Yes | `company`, `team`, `people`, `skills-matrix` |
| last_updated | date | Yes | `YYYY-MM-DD` |
| tags | list | Yes | `context` + additional as relevant |

**Root index files (decisions, pendings, ideas):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | `index` |
| subtype | string | Yes | `decisions`, `pendings`, `ideas` |
| last_updated | date | Yes | `YYYY-MM-DD` |
| tags | list | Yes | `decisions` or `index` |

**Daily briefs:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | `daily-brief` |
| date | date | Yes | `YYYY-MM-DD` |
| tags | list | Yes | `daily-brief` |

**MOC/Index files:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | `moc` |
| subtype | string | Yes | `vault-index`, `meetings`, `projects` |
| tags | list | Yes | `index` |

**Inbox items (auto-generated by autonomous monitor):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `inbox-item` |
| source | string | Yes | `slack-monitor` or `gmail-triage` |
| generated | datetime | Yes | ISO 8601 with timezone (`-03:00`) |
| device | string | Yes | `pc-empresa`, `pc-pessoal`, `notebook`, or `unknown` |
| channels_scanned | number | slack-monitor only | Number of Slack channels checked |
| channels_with_activity | number | slack-monitor only | Channels with messages found |
| emails_scanned | number | gmail-triage only | Total emails checked |
| emails_relevant | number | gmail-triage only | Emails that passed filters |
| tags | list | No | Optional |

**Monitor errors:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `monitor-error` |
| source | string | Yes | `inbox-processor`, `slack-monitor`, or `gmail-triage` |
| generated | datetime | Yes | ISO 8601 with timezone |
| device | string | Yes | Device identifier |

**Support issues:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| type | string | Yes | Always `support-issue` |
| issue_id | string | Yes | `"PP-NNN"` format |
| title | string | Yes | Human-readable issue title |
| status | string | Yes | `pendente`, `em andamento`, `corrigido`, `não é falha` (always lowercase) |
| spreadsheet | string | Yes | Planilha name or `"Todas"` |
| first_seen | date | Yes | `YYYY-MM-DD` |
| clickup_id | string | If known | Legacy ClickUp task ID |
| occurrence_log | list of objects | Yes | `[{date, channel, context}]` — single source of truth for occurrences |
| tags | list | Yes | `support/issue`, `project/pacote-planilhas` |

#### Tag Taxonomy (hierarchical, lowercase kebab-case)

| Category | Tags | Usage |
|----------|------|-------|
| Meetings | `meeting/1on1`, `meeting/weekly`, `meeting/project`, `meeting/standalone` | On meeting records |
| Projects | `project/<project-kebab>` (e.g., `project/projeto-alpha`), `project/active`, `project/completed` | On project context files and project meetings |
| Preps | `prep/1on1`, `prep/weekly` | On preparation briefings |
| Roles | `role/board`, `role/direct-report`, `role/external` | On person profiles — cross-cutting categories |
| Companies | `company/partner`, `company/active` | On company context files in `companies/` |
| Support | `support/issue` | On support issue files in `projects/pacote-planilhas/support/` |
| Other | `context`, `development`, `decisions`, `index`, `daily-brief` | On respective file types |

#### Wikilink Rules

- All person mentions in body text → `[[Full Name]]` (e.g., `[[Team Member]]`, `[[Owner Name]]`)
- All project references in body text → `[[Project Display Name]]` (e.g., `[[{{PROJECT_NAME}}]]`)
- Cross-meeting references → `[[YYYY-MM-DD 1on1 FirstName]]`, `[[YYYY-MM-DD weekly]]`, or `[[YYYY-MM-DD project-kebab]]`
- Standalone meeting references → `[[YYYY-MM-DD category description]]` (e.g., `[[2026-03-16 alinhamento stakeholder]]`)
- Context file references in body text → `[[file-name]]` (e.g., `[[company]]`, `[[team]]`)
- **Never use `[text](path)` markdown links for internal vault references** — always use `[[wikilinks]]`
- **Keep `@path` references in CLAUDE.md** — those serve Claude Code file inclusion; wikilinks go in content files only
- All wikilink values in YAML frontmatter MUST be double-quoted strings: `"[[Name]]"`

#### Dataview Queries

Embed Dataview query blocks in:
- Person profiles: skills matrix (reads from own `skills` frontmatter) + recent meetings for that person (at bottom, before nav footer)
- Skills matrix dashboard: consolidated competency table (reads from all profiles via `dataviewjs`)
- Project context files: recent project meetings (at bottom)
- MOC files: aggregated dashboards (meetings, projects)

#### Navigation Footer

Every meeting record and prep ends with a navigation footer:
```
---
**See also:** [[Person or Project]] | [[MOC Meetings]]
```

### Meeting Records
- Always use the template from `templates/` (meeting.md for 1:1s, weekly.md for weeklys, project-meeting.md for project meetings)
- All meeting records MUST include YAML frontmatter matching the Obsidian Conventions schema above
- 1:1s always start with **Personal Check-in** section
- Action items MUST have an owner and deadline
- Previous action items MUST be reviewed with status update
- Decisions MUST be documented with rationale

### Standalone Meetings

Standalone meetings are multi-topic meetings that reference **2+ projects** without belonging to any single one. Examples: alignment meetings, strategy sessions, board/CEO discussions, ad-hoc cross-project syncs.

**Location:** `projects/standalone-meetings/meetings/YYYY-MM-DD/`

**File naming:** `YYYY-MM-DD <category> <description>.md` (e.g., `2026-03-16 alinhamento stakeholder.md`, `2026-03-17 diretoria projeto-x.md`)

**Categories:**

| Category | Usage |
|----------|-------|
| `alinhamento` | Stakeholder alignment on priorities/status |
| `estrategica` | Vision, roadmap, positioning discussions |
| `ad-hoc` | One-off meeting without clear category |
| `diretoria` | Board/CEO, corporate topics |

**Detection:** Automatic when 2+ projects are discussed in a single meeting. If a meeting starts as a project meeting but covers multiple projects substantially, it should be reclassified as standalone.

**Propagation:** After creating the standalone record, decisions, risks, and notes are propagated to each referenced project's context file (in `projects/<project>/`). Each project gets a summarized entry with a wikilink back to the standalone record.

**Frontmatter:** Uses `subtype: standalone`, `category`, and `projects_discussed` fields (see YAML schema above). Tag: `meeting/standalone`.

**Template:** `templates/standalone-meeting.md`

**Reference:** Decision #47.

### Task Management
- **ClickUp** = all task management (the owner's tasks and team tasks) — see `docs/reference/integrations.md`
- `context/pendings.md` = things **Claude needs from the owner** to operate the system
- `context/decisions.md` = centralized log of all decisions made in meetings — consulted during preparation, appended during processing
- Tasks always include Source in description (e.g., "Source: 1:1 TeamMember 2026-02-12", "Source: Reunião projeto-x 2026-03-10", "Source: Pedido direto")
- No deadline → ask the owner immediately, don't create without asking
- Always assign tasks to the responsible person
- Route tasks by topic, not by person (see routing rules in `docs/reference/integrations.md`)

### Development Plans
- Update after meetings where development was discussed
- Add progress log entries with dates
- Review competency levels quarterly
- the owner's own development tracked at `team/<owner-slug>/<Owner Name> dev-plan.md` — update Situation Log after meetings where management behaviors were observed

### Companies

- `companies/` — context documents for external companies (partners, clients)
- Template: `templates/company.md`
- Frontmatter: `type: company`, `name`, `aliases`, `status`, `tags`
- Companies without documents exist in the wikilink index with `file: null` (aliases still work for text matching)

### Design System Schema 2.0

Design-system JSON files in `presentations-design-systems/` use schema version `2.0` (breaking change from 1.0). All sections are REQUIRED; validators in `scripts/validate_design_system.py` enforce presence + format.

**Required top-level fields:**

| Field | Type | Validation |
|-------|------|------------|
| `schema_version` | string | Must be `"2.0"` |
| `name` | string | kebab-case |
| `base_mode` | string | `"light"` or `"dark"` |
| `intended_background_hex` | string | 6-digit hex |
| `palette` | object | 9 roles (fg, fg_muted, fg_subtle, primary, secondary, accent, success, danger, rule) |
| `typography` | object | display/body/mono fonts + 7-key scale (xs..hero) |
| `spacing` | object | 5 keys (xs/sm/md/lg/xl) + slide_padding |
| `layout` | object | slide_size, safe_area_inset, slide_number, logo |
| `components` | object | big_number, callout, quote, list_item |
| `iconography` | object | style + weight + library_preference |
| `voice` | object | **NEW in 2.0** |
| `brand` | object | **NEW in 2.0** |
| `anti_patterns` | list | **NEW in 2.0** |

**Voice schema:**

```json
"voice": {
  "tone_descriptors": ["direto", "técnico-acessível", "provocativo"],
  "vocabulary_preferred": ["construir", "operar", "alavancar"],
  "vocabulary_banned": ["sinérgico", "disruptivo", "ecossistema"]
}
```

Each array: min 3 non-empty strings.

**Brand schema:**

```json
"brand": {
  "archetype": "explorer",
  "personality": ["confiante", "curioso", "irreverente"],
  "audience_voice_match": "experts em e-commerce"
}
```

- `archetype`: one of Jungian 12 — `explorer | sage | hero | rebel | ruler | magician | outlaw | jester | caregiver | innocent | everyman | lover`
- `personality`: min 3 non-empty strings
- `audience_voice_match`: non-empty string

**Anti-patterns schema:**

```json
"anti_patterns": [
  {
    "pattern": "Gradiente roxo em fundo branco",
    "example": "background: linear-gradient(to right, #6b46c1, #ffffff)",
    "reason": "Cliché de AI-slop reconhecido visualmente"
  }
]
```

Array of 3-8 items, each with non-empty `pattern`, `example`, `reason` strings.

**Where these fields are consumed:**

- `voice` — `cos-create-presentation` Phase 5.5 audit P1 (Comunicador); reservado para Phase 5 authoring em sub-plans futuros
- `brand` — `cos-create-presentation` Phase 5.5 audit P3 (Pedagogo)
- `anti_patterns` — `cos-create-presentation` Phase 5.5 audit P2 (Designer Visual) + Quality gate 5.5.4

**Migration from 1.0:**

Existing DSs must be migrated. Validator rejects DSs without `schema_version: "2.0"`. CSS generator (`scripts/generate_ds_css.py`) asserts schema 2.0 at runtime.

**Reference:** `docs/superpowers/specs/2026-05-20-cos-presentation-design-intelligence-design.md` section 2.
