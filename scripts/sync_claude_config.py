#!/usr/bin/env python3
"""
sync_claude_config.py — UserPromptSubmit hook for .claude/ <-> _claude/ sync.

Obsidian Sync ignores hidden folders (.claude/), so skills and settings
would be lost when switching devices. This script maintains a visible
mirror at _claude/ that Obsidian Sync handles normally.

Sync logic:
  - For each file, compare timestamps in both directories.
  - If _claude/ is newer  -> copy to .claude/  (incoming from another device)
  - If .claude/ is newer  -> copy to _claude/  (local change, needs to sync out)
  - If file exists only in one side -> copy to the other

Scope: only syncs skills/ and settings*.json (not projects/, sessions, etc.)

Output: JSON to stdout (hookSpecificOutput format) when changes are made.
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAULT_ROOT = Path(__file__).resolve().parent.parent
HIDDEN_DIR = VAULT_ROOT / ".claude"
MIRROR_DIR = VAULT_ROOT / "_claude"
LOG_PATH = VAULT_ROOT / "scripts" / "sync_claude_config.log"

# What to sync — relative paths from .claude/ root
# NOTE: settings.local.json is excluded — it contains machine-specific paths
# (env vars, additionalDirectories) that differ between devices.
SYNC_PATTERNS = {
    "skills": "dir",        # entire directory tree
    "settings.json": "file",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Append message to log file. Never raises."""
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------

def collect_files(base: Path) -> dict[str, Path]:
    """Collect all syncable files under base, returning {relative_path: absolute_path}."""
    files = {}
    for name, kind in SYNC_PATTERNS.items():
        source = base / name
        if kind == "dir":
            if source.is_dir():
                for f in source.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(base)).replace("\\", "/")
                        files[rel] = f
            else:
                log(f"  collect_files: dir not found: {source}")
        elif kind == "file":
            if source.is_file():
                files[name] = source
            else:
                log(f"  collect_files: file not found: {source}")
    log(f"  collect_files({base.name}): {len(files)} files")
    return files


def sync_file(src: Path, dst: Path) -> None:
    """Copy src to dst, creating parent dirs as needed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def run_sync() -> dict:
    """Execute bidirectional sync. Returns summary of changes."""
    changes = {"hidden_to_mirror": [], "mirror_to_hidden": [], "errors": []}

    if not HIDDEN_DIR.exists() and not MIRROR_DIR.exists():
        log("Both dirs missing, nothing to sync")
        return changes

    # Ensure both dirs exist
    HIDDEN_DIR.mkdir(parents=True, exist_ok=True)
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)

    log("Collecting files...")
    hidden_files = collect_files(HIDDEN_DIR)
    mirror_files = collect_files(MIRROR_DIR)

    all_keys = set(hidden_files.keys()) | set(mirror_files.keys())

    for rel in sorted(all_keys):
        h_path = hidden_files.get(rel)
        m_path = mirror_files.get(rel)

        try:
            if h_path and not m_path:
                # exists only in .claude/ -> copy to _claude/
                dst = MIRROR_DIR / rel
                sync_file(h_path, dst)
                changes["hidden_to_mirror"].append(rel)

            elif m_path and not h_path:
                # exists only in _claude/ -> copy to .claude/
                dst = HIDDEN_DIR / rel
                sync_file(m_path, dst)
                changes["mirror_to_hidden"].append(rel)

            elif h_path and m_path:
                h_mtime = h_path.stat().st_mtime
                m_mtime = m_path.stat().st_mtime

                if abs(h_mtime - m_mtime) < 1.0:
                    continue  # same timestamp, skip

                if m_mtime > h_mtime:
                    # mirror is newer -> update hidden
                    sync_file(m_path, h_path)
                    changes["mirror_to_hidden"].append(rel)
                else:
                    # hidden is newer -> update mirror
                    sync_file(h_path, m_path)
                    changes["hidden_to_mirror"].append(rel)

        except Exception as e:
            changes["errors"].append(f"{rel}: {e}")
            log(f"ERROR syncing {rel}: {e}")

    # Clean up: remove files from mirror that were deleted from hidden
    for rel in sorted(mirror_files.keys() - hidden_files.keys()):
        # This case is already handled above (mirror_to_hidden),
        # but if we want to handle deletions, we'd need a manifest.
        # For now, we don't delete — only add/update.
        pass

    return changes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log("--- Hook invoked ---")
    log(f"Python: {sys.executable} {sys.version}")
    log(f"CWD: {Path.cwd()}")
    log(f"VAULT_ROOT: {VAULT_ROOT}")
    log(f"HIDDEN_DIR exists: {HIDDEN_DIR.exists()}")
    log(f"MIRROR_DIR exists: {MIRROR_DIR.exists()}")

    try:
        changes = run_sync()

        total = (
            len(changes["hidden_to_mirror"])
            + len(changes["mirror_to_hidden"])
            + len(changes["errors"])
        )

        log(f"Sync result: {total} changes (export={len(changes['hidden_to_mirror'])}, import={len(changes['mirror_to_hidden'])}, errors={len(changes['errors'])})")

        if total == 0:
            log("No changes, exiting silently")
            sys.exit(0)

        # Build summary for Claude
        parts = []
        if changes["mirror_to_hidden"]:
            parts.append(
                f"Imported from _claude/ (other device): {', '.join(changes['mirror_to_hidden'])}"
            )
        if changes["hidden_to_mirror"]:
            parts.append(
                f"Exported to _claude/ (for sync): {', '.join(changes['hidden_to_mirror'])}"
            )
        if changes["errors"]:
            parts.append(f"Errors: {', '.join(changes['errors'])}")

        summary = "; ".join(parts)
        log(f"Sync completed: {summary}")

        # Output for Claude hook system
        output = {
            "hookSpecificOutput": f"[claude-config-sync] {summary}",
        }
        json_output = json.dumps(output)
        log(f"stdout -> {json_output}")
        print(json_output)

    except Exception as e:
        import traceback
        log(f"FATAL: {e}\n{traceback.format_exc()}")
        sys.exit(0)  # don't block Claude on errors


if __name__ == "__main__":
    main()
