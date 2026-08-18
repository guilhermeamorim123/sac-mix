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
| `transcrever_audio.py` | Manual (per meeting) | Claude runs during meeting processing | Transcribe audio locally via faster-whisper (no API, no ffmpeg) |

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

**What:** Transcribes meeting audio into the vault using **faster-whisper**, running entirely on the local machine. No audio leaves the vault and no API key is needed.

**When to run:** During meeting processing workflows when an audio file is provided. Also usable standalone (`--type note`) to transcribe a dictated voice memo.

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

# Loose dictation — writes <audio>.txt beside the file, moves nothing
python scripts/transcrever_audio.py "ideia.m4a" --type note
```

**Flags:** `--model` (`tiny|base|small|medium|large-v3`, default `small`, or set `WHISPER_MODEL`), `--language` (default `pt`), `--prompt` (extra vocabulary for one run), `--keep-original` (don't move the audio).

**Behavior:**
1. Creates meeting folder in the correct location:
   - 1:1: `team/<member>/meetings/YYYY-MM-DD/`
   - Weekly: `weeklys/YYYY-MM-DD/`
   - Project: `projects/<project>/meetings/YYYY-MM-DD/`
   - Note: alongside the audio file
2. Moves original audio to the folder as `original.<ext>` — **after** a successful transcription, so a failure never misplaces the recording
3. Primes Whisper with vault proper nouns (see Vocabulary below) — this is what separates `Mix Conecta` from `nomics conecta`
4. Transcribes with silence filtering, printing live progress
5. Saves `transcription.txt` and `transcription-timestamped.txt`

No format conversion or chunking step: PyAV decodes m4a/mp3/wav/mp4 directly, and local transcription has no upload size limit.

**Vocabulary:** terms come from `context/vocabulario.txt` (hand-maintained, highest priority), then person filenames in `team/`/`people/`, project and company folder names, and capitalized `[[wikilinks]]` in content folders. Templates and docs are excluded — their placeholders (`[[Full Name]]`, `[[Project A]]`) would bias the transcription toward words nobody said. Add any term Whisper keeps mangling to `context/vocabulario.txt`.

**Dependencies:** self-bootstrapping. First run creates `scripts/.venv-whisper/` (gitignored) and installs `av==13.1.0` + `faster-whisper`, then re-executes itself inside it. Any Python 3.9+ works as the entry point. **No ffmpeg and no Homebrew required** — `av` is pinned to 13.1.0 because 14.x ships no macOS x86_64 wheel for Python 3.9 and would try to compile from source.

The model downloads on first use to `~/.cache/huggingface` (~500 MB for `small`). Measured on this Intel Mac: `small` runs at roughly 1x real time (a 60-minute meeting takes about an hour), `base` at ~2.5x with noticeably worse punctuation.

**Output:** `transcription.txt` + `transcription-timestamped.txt` in the meeting folder.

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
