# Scripts Reference

> **Purpose:** Document all scripts in `scripts/` — what they do, how to run, and whether they're manual or automated.

---

## Overview

| Script | Type | Trigger | Purpose |
|--------|------|---------|---------|
| `setup_mac.sh` | Manual (once per macOS device) | User runs after cloning | Full macOS onboarding — wraps the two scripts below plus env var, whatsapp-mcp clone and secret protection |
| `bootstrap_claude.py` | Manual (once per device) | User runs on new device | Copy `_claude/` → `.claude/` for first-time setup |
| `sync_claude_config.py` | Hook (automatic) | `UserPromptSubmit` | Keep `.claude/` ↔ `_claude/` in sync across devices |
| `wikilink_hook.py` | Hook (automatic) | `PostToolUse` (Write/Edit) | Validate wikilinks and tags in vault `.md` files |
| `seed_wikilink_index.py` | Manual (as needed) | User or Claude runs | Build/rebuild `wikilink-index.json` from vault files |
| `transcrever_audio.py` | Manual (per meeting) | Claude runs during meeting processing | Transcribe audio files via Whisper |

---

## Manual Scripts

### `setup_mac.sh`

**What:** One-shot onboarding of the vault on a fresh macOS machine. Idempotent — safe to re-run.

**Usage:**
```bash
git clone https://github.com/guilhermeamorim123/sac-mix.git ~/"Chief of Staff"
cd ~/"Chief of Staff"
bash scripts/setup_mac.sh
```

**Behavior:**
1. Verifies `git`, `python3`, `uv`, `go`, `node` and `claude` are installed — exits with install instructions if any are missing
2. Runs `bootstrap_claude.py` and `seed_wikilink_index.py`
3. Clones `whatsapp-mcp` from upstream (it is gitignored here because it carries its own `.git`)
4. Appends `**/.claude/settings.local.json` to `~/.config/git/ignore` so the token file cannot be committed
5. Appends `export CLAUDE_CODE_FORK_SUBAGENT=1` to `~/.zshrc`
6. Prints the remaining manual steps: WhatsApp QR pairing, `buscapp/.env.local`, Claude Code login

**Dependencies:** bash (macOS default). Does not install anything itself.

---

### `bootstrap_claude.py`

**What:** First-time setup of `.claude/` on a new device. Copies the visible mirror (`_claude/`, delivered by Obsidian Sync) into the hidden `.claude/` directory that Claude Code needs.

**When to run:** Once per new device, after Obsidian Sync has delivered the vault.

**Usage:**
```bash
python scripts/bootstrap_claude.py
```

**Behavior:**
1. Checks `_claude/` exists and is not empty
2. If `.claude/skills/` already has files, asks for confirmation before overwriting
3. Copies all files from `_claude/` to `.claude/`
4. After this, the `sync_claude_config.py` hook keeps everything in sync automatically

**Dependencies:** None (stdlib only).

**Output:** Progress log to stdout.

---

### `seed_wikilink_index.py`

**What:** Scans the vault and builds `scripts/wikilink-index.json` — the lookup table used by `wikilink_hook.py` to resolve `[[wikilinks]]`.

**When to run:**
- First-time vault setup
- When the wikilink hook reports many false "unresolved" links
- After bulk file renames or restructuring

**Usage:**
```bash
python scripts/seed_wikilink_index.py            # Generate (skips if exists)
python scripts/seed_wikilink_index.py --rebuild   # Force regenerate
```

**Dependencies:** None (stdlib only).

**Output:** `scripts/wikilink-index.json`

---

### `transcrever_audio.py`

**What:** Transcribes meeting audio files using OpenAI Whisper. Handles file organization, format conversion, chunking, and transcription.

**When to run:** During meeting processing workflows when an audio file is provided.

**Usage:**
```bash
# 1:1 meeting
python scripts/transcrever_audio.py "gravacao.m4a" team-member-slug

# Weekly
python scripts/transcrever_audio.py "weekly.m4a" --type weekly

# Project meeting
python scripts/transcrever_audio.py "reuniao.m4a" --type project --project project-slug

# With explicit date
python scripts/transcrever_audio.py "gravacao.m4a" team-member-slug --date 2026-03-23
```

**Behavior:**
1. Creates meeting folder in the correct location:
   - 1:1: `team/<member>/meetings/YYYY-MM-DD/`
   - Weekly: `weeklys/YYYY-MM-DD/`
   - Project: `projects/<project>/meetings/YYYY-MM-DD/`
2. Moves original audio to the folder as `original.<ext>`
3. Converts to WAV (16kHz, mono, PCM) for Whisper compatibility
4. Splits WAV into chunks if > 24MB
5. Transcribes via Whisper and saves `transcription.txt`

**Dependencies:** `openai` (Python package), `ffmpeg` (system binary).

**Output:** `transcription.txt` in the meeting folder.

---

## Hook Scripts

### `sync_claude_config.py`

**What:** Bidirectional sync between `.claude/` (hidden, ignored by Obsidian Sync) and `_claude/` (visible mirror, synced normally).

**Trigger:** `UserPromptSubmit` hook — runs on every message the user sends to Claude.

**What gets synced:**
- `skills/` — all CoS slash command definitions (recursive)
- `settings.json` — project permissions, hooks, plugins

**Excluded:** `settings.local.json` — machine-specific (env vars, paths). Each device maintains its own.

**Sync logic:**
- Newer file wins (timestamp comparison, ±1s tolerance)
- Files in only one side get copied to the other
- No deletion propagation (to delete, remove from both sides)

**Dependencies:** None (stdlib only).

**Output:** JSON to stdout (`hookSpecificOutput`) when changes are made. Silent when in sync.

**Log:** `scripts/sync_claude_config.log`

**See also:** `docs/reference/hooks.md` for full architecture and troubleshooting.

---

### `wikilink_hook.py`

**What:** Post-tool hook that validates wikilinks and tags after any Write/Edit on vault `.md` files.

**Trigger:** `PostToolUse` hook — runs after Write or Edit on files in content folders (`team/`, `projects/`, `people/`, `companies/`, `weeklys/`, `daily-briefs/`, `context/`).

**Behavior:**
1. Extracts all `[[wikilinks]]` and `#tags` from the modified file
2. Compares against `scripts/wikilink-index.json`
3. Auto-updates the index for resolvable references
4. Outputs alerts via `additionalContext` for unresolved references and new entities

**Dependencies:** None (stdlib only). Requires `scripts/wikilink-index.json` (generated by `seed_wikilink_index.py`).

**Log:** `scripts/wikilink_hook.log`

**See also:** `docs/reference/hooks.md` for troubleshooting.

---

## Data Files

| File | Generated by | Purpose |
|------|-------------|---------|
| `wikilink-index.json` | `seed_wikilink_index.py` / `wikilink_hook.py` | Wikilink resolution lookup table |
| `wikilink_hook.log` | `wikilink_hook.py` | Hook execution log |
| `sync_claude_config.log` | `sync_claude_config.py` | Sync execution log |
| `initial-companies.json` | Manual (seed data) | Initial company entries for wikilink index |

---

## Adding New Scripts

1. Place in `scripts/` following existing patterns:
   - Docstring with purpose, usage, and examples
   - `VAULT_ROOT = Path(__file__).resolve().parent.parent`
   - Stdlib-only when possible (no pip installs for hooks)
   - Hooks: JSON output to stdout, silent on no-op, never raise blocking exceptions
2. If it's a hook, register in `.claude/settings.json` and document in `docs/reference/hooks.md`
3. Document in this file following the same format
4. Run `python scripts/sync_claude_config.py` if settings changed

---
**See also:** `docs/reference/hooks.md` | `.claude/settings.json`
