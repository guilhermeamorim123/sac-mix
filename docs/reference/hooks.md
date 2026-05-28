# Hooks Reference

> **Purpose:** Document all Claude Code hooks configured in this project — what they do, when they fire, and how to troubleshoot.
>
> **Config file:** `.claude/settings.json` → `hooks` key

---

## Overview

| Hook | Event | Matcher | `if` Condition | Script | Purpose |
|------|-------|---------|----------------|--------|---------|
| Config Sync | `UserPromptSubmit` | `""` (all) | — | `scripts/sync_claude_config.py` | Keep `.claude/` and `_claude/` in sync across devices |
| Wikilink Manager (Write) | `PostToolUse` | `Write` | `Write(*.md)` | `scripts/wikilink_hook.py` | Validate wikilinks and tags in vault markdown files |
| Wikilink Manager (Edit) | `PostToolUse` | `Edit` | `Edit(*.md)` | `scripts/wikilink_hook.py` | Validate wikilinks and tags in vault markdown files |

---

## Hook 1: Config Sync (`sync_claude_config.py`)

### Problem

Obsidian Sync ignores hidden folders (those starting with `.`). The `.claude/` directory contains skills (slash commands) and settings that are essential for the CoS to function. When switching devices, these files would be missing.

### Solution

A visible mirror folder `_claude/` in the vault root is synced by Obsidian Sync normally. A hook runs on every prompt submission to keep both directories in sync.

### Architecture

```
Device A                              Device B
─────────                             ─────────
.claude/skills/ ←→ _claude/skills/  ☁️  _claude/skills/ ←→ .claude/skills/
  (hidden)          (visible)            (visible)          (hidden)
                        ↕                    ↕
                   Obsidian Sync ←────→ Obsidian Sync
```

### New Device Setup (Bootstrap)

The sync hook lives inside `.claude/settings.json`, which doesn't exist on a fresh device. To break this chicken-and-egg problem, run the bootstrap script **once** after Obsidian Sync delivers the vault:

```bash
python scripts/bootstrap_claude.py
```

This copies `_claude/` → `.claude/`. After that, the hook keeps everything in sync automatically.

See `docs/reference/scripts.md` for details.

### Sync Rules

| Scenario | Action |
|----------|--------|
| File exists only in `.claude/` | Copy to `_claude/` (export for sync) |
| File exists only in `_claude/` | Copy to `.claude/` (import from other device) |
| Both exist, `_claude/` newer | Copy to `.claude/` (incoming change) |
| Both exist, `.claude/` newer | Copy to `.claude/` (local change) |
| Both exist, same timestamp (±1s) | Skip (already in sync) |

### What Gets Synced

Only essential config files — not sessions, cache, or history:

| Path | Type | Description |
|------|------|-------------|
| `skills/` | Directory (recursive) | All CoS slash command definitions |
| `settings.json` | File | Project permissions, hooks, plugins |

**Excluded:** `settings.local.json` — contains machine-specific values (env vars, paths, `additionalDirectories`) that differ between devices. Each device maintains its own copy.

### Event

- **Trigger:** `UserPromptSubmit` — fires on every message the user sends
- **Matcher:** `""` (empty = matches all prompts)
- **Why this event:** Guarantees sync happens at conversation start, before any skill might be invoked. Lightweight enough to run on every prompt (typical execution: <50ms when nothing changed)

### Output

When changes are detected, outputs JSON to stdout:

```json
{
  "hookSpecificOutput": "[claude-config-sync] Imported from _claude/ (other device): skills/cos-daily-brief/SKILL.md; Exported to _claude/ (for sync): settings.json"
}
```

Silent exit (no output) when everything is already in sync.

### Log File

`scripts/sync_claude_config.log` — records all sync operations and errors.

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Skills missing after switching device | `_claude/` not synced yet by Obsidian | Wait for Obsidian Sync to complete, then send any message to trigger hook |
| Hook not firing | `settings.json` doesn't have the hook | Check `.claude/settings.json` → `hooks.UserPromptSubmit` exists |
| Stale files in mirror | Script error | Check `scripts/sync_claude_config.log` for errors |
| `_claude/` not visible in Obsidian | Obsidian might hide `_` prefixed folders | Check Files & Links settings in Obsidian |

### Limitations

- **No deletion propagation:** If a file is deleted from `.claude/`, it will be re-created from `_claude/` on next sync (and vice versa). To truly delete a skill, remove it from both directories.
- **Conflict resolution is timestamp-based:** If the same file is edited on two devices before sync, the newer timestamp wins. This is acceptable because skill edits are rare and single-author.
- **`settings.local.json` not synced:** This file is machine-specific (env vars, paths). Each device maintains its own copy of env vars and paths.

---

## Hook 2: Wikilink Manager (`wikilink_hook.py`)

### Purpose

Maintains wikilink consistency across the vault. After any Write or Edit on a markdown file, it:

1. Extracts all `[[wikilinks]]` and `#tags` from the modified file
2. Compares against the wikilink index (`scripts/wikilink-index.json`)
3. Auto-updates the index for resolvable references
4. Alerts Claude (via `additionalContext` in output) about:
   - Unresolved wikilinks (no matching file in vault)
   - New entities that may need a profile or project file created

### Event

- **Trigger:** `PostToolUse` — fires after Write or Edit tool completes
- **Matchers:** Two separate entries — `Write` and `Edit` — each with an `if` condition
- **`if` condition:** `Write(*.md)` and `Edit(*.md)` — Claude Code v2.1.85+ skips process spawning entirely when the file path doesn't end in `.md`
- **Scope:** Only processes `.md` files in content folders (`team/`, `projects/`, `people/`, `companies/`, `weeklys/`, `daily-briefs/`, `context/`)

### `if` Conditional (v2.1.85+)

The `if` field is placed on each individual hook object and uses permission rule syntax. For `Write` and `Edit`, the pattern matches against `file_path`:

```json
{
  "type": "command",
  "command": "python \"$CLAUDE_PROJECT_DIR/scripts/wikilink_hook.py\"",
  "if": "Write(*.md)"
}
```

- `Write(*.md)` — only runs when the file path ends with `.md`
- `Edit(*.md)` — same for Edit
- Claude Code evaluates the condition **before spawning the subprocess**, so editing `.json`, `.py`, `.js`, or other non-markdown files produces zero overhead
- The `if` field only works on `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, and `PermissionRequest` events — not on `UserPromptSubmit` (which is why Config Sync has no `if`)

### Index

The wikilink index lives at `scripts/wikilink-index.json`. It maps display names to file paths for fast lookups. Seeded by `scripts/seed_wikilink_index.py`.

### Log File

`scripts/wikilink_hook.log`

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Hook fires on non-vault files | File is in a content folder | Expected behavior — hook checks folder membership |
| False "unresolved" alerts | Index out of date | Run `python scripts/seed_wikilink_index.py` to rebuild |
| Hook errors on every edit | Python or path issue | Check `scripts/wikilink_hook.log` |

---

## Adding New Hooks

To add a new hook:

1. Create the script in `scripts/` following the existing pattern:
   - Docstring explaining purpose
   - `VAULT_ROOT` derived from `Path(__file__).resolve().parent.parent`
   - Log file at `scripts/<name>.log`
   - JSON output to stdout using `hookSpecificOutput` key
   - Silent exit on no-op (don't flood Claude with empty results)
   - Never raise exceptions that would block Claude — wrap in try/except

2. Register in `_claude/settings.json` (the visible mirror — not `.claude/` directly) under the appropriate event:
   - `UserPromptSubmit` — runs on every user message
   - `PostToolUse` — runs after a tool executes (use `matcher` to filter)
   - `PreToolUse` — runs before a tool executes
   - `Notification` — runs on system notifications
   - `Stop` — runs when Claude stops generating

3. Add an `if` condition when the hook should only run for specific file types or patterns (Claude Code v2.1.85+):
   - Use permission rule syntax: `ToolName(pattern)` — e.g., `Write(*.md)`, `Edit(*.py)`, `Bash(git *)`
   - Only supported for tool events (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`)
   - The `if` field goes on the individual hook object (alongside `type` and `command`), not on the matcher group
   - When using `if`, split combined matchers (e.g., `Write|Edit`) into separate matcher groups — one per tool — because each `if` condition can only reference one tool name

4. Document in this file following the same format.

5. The Config Sync hook will automatically propagate `_claude/settings.json` → `.claude/settings.json` on the next prompt submission. To sync immediately, run `python scripts/sync_claude_config.py`.

---
**See also:** `.claude/settings.json` | `scripts/`
