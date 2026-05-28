---
type: reference
---

# Obsidian Tasks — Vault Task Convention

> How the CoS tracks tasks when ClickUp is OFF (vault-first). Requires the **Tasks** and **Dataview** community plugins. When `integrations.clickup: true`, ClickUp is the source of truth and this convention is the supplement; when `false`, this is the only task layer.

## Syntax (Obsidian Tasks plugin)
A task is a Markdown checkbox with optional emoji metadata:

```
- [ ] Descrição da tarefa 📅 2026-06-01 🔼 #task
- [x] Tarefa concluída ✅ 2026-05-20
```

- `📅 YYYY-MM-DD` — due date
- `⏳ YYYY-MM-DD` — scheduled date
- `🔺 / ⏫ / 🔼 / 🔽` — priority (highest to low)
- `#task` — tag so Dataview/Tasks queries can find it
- `✅ YYYY-MM-DD` — completion date (added when checked)
- Assignee (optional): `[[Member Name]]` inside the text

## Where tasks live
- **Project tasks** → in the project note `projects/<slug>/<Project>.md`, under a `## Tarefas` section.
- **Personal / owner tasks** → in `context/pendings.md` or the relevant daily-brief.
- **Delegated tasks** → canonical home is the project note with a `[[Member Name]]` tag.

## How skills use it
- `cos-project-management`: when ClickUp is off, create/update tasks as checkboxes under `## Tarefas` in the project note instead of calling ClickUp.
- `cos-daily-brief`: the vault loader scans open `- [ ]` tasks with `📅` due dates across `projects/`, `context/`, and recent daily-briefs, and reports overdue / due-today / next-3-days. When ClickUp is on, ClickUp tasks lead and vault tasks supplement.

## Dataview query (drop into any note to see open tasks)
```dataview
TASK
WHERE !completed AND due
SORT due ASC
```
