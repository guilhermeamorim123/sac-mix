---
type: project
name: "{{PROJECT}}"
status: "{{STATUS}}"
owner: "[[{{OWNER}}]]"
clickup_list: "{{CLICKUP_LIST}}"
started: {{START_DATE}}
tags:
  - project/{{PROJECT_KEBAB}}
  - project/active
---

# {{PROJECT}}

## Description

<!-- What is this project about, why does it exist, what problem does it solve -->

## Participants

| Name | Role in Project | Notes |
|------|----------------|-------|
| ...  | ...            | ...   |

## Meetings

| Date | Key Outcome | Record |
|------|-------------|--------|
| YYYY-MM-DD | [Brief summary] | [meetings/YYYY-MM-DD/meeting.md] |

## Key Decisions

<!-- Aggregated from all meetings — quick reference without reading every record -->

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | ...  | ...      | ...       |

## Current Risks & Blockers

| # | Risk/Blocker | Severity | Owner | Status |
|---|-------------|----------|-------|--------|
| 1 | ...         | ...      | ...   | Open/Mitigated/Closed |

## Notes

<!-- Anything else relevant to this project's history -->

## Meeting History

```dataview
TABLE date AS "Date"
FROM #meeting WHERE contains(file.outlinks, this.file.link)
SORT date DESC
```

## Tarefas

> Quando o ClickUp está off, as tarefas do projeto vivem aqui como checkboxes (ver `docs/reference/obsidian-tasks.md`).

- [ ] Exemplo de tarefa 📅 2026-06-01 #task

---
**See also:** [[MOC Projects]] | [[MOC Meetings]]