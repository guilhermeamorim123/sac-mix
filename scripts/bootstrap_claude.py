#!/usr/bin/env python3
"""
bootstrap_claude.py — First-time setup of .claude/ on a new device.

Obsidian Sync delivers _claude/ (visible mirror) but not .claude/ (hidden).
This script copies _claude/ -> .claude/ so that Claude Code can find its
skills and settings. Run once per new device, then the UserPromptSubmit
hook (sync_claude_config.py) keeps everything in sync automatically.

Usage:
    python scripts/bootstrap_claude.py
"""

import shutil
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
MIRROR_DIR = VAULT_ROOT / "_claude"
HIDDEN_DIR = VAULT_ROOT / ".claude"


def main() -> None:
    # Check _claude/ exists (delivered by Obsidian Sync)
    if not MIRROR_DIR.exists():
        print("ERROR: _claude/ not found in vault root.")
        print("Wait for Obsidian Sync to finish, then try again.")
        sys.exit(1)

    mirror_files = list(MIRROR_DIR.rglob("*"))
    file_count = sum(1 for f in mirror_files if f.is_file())

    if file_count == 0:
        print("ERROR: _claude/ exists but is empty. Obsidian Sync may still be running.")
        sys.exit(1)

    # Check if .claude/ already has skills
    existing_skills = list((HIDDEN_DIR / "skills").rglob("*.md")) if (HIDDEN_DIR / "skills").exists() else []
    if existing_skills:
        print(f".claude/skills/ already has {len(existing_skills)} files.")
        answer = input("Overwrite with _claude/ contents? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    # Copy _claude/ -> .claude/
    HIDDEN_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    for src in mirror_files:
        if not src.is_file():
            continue
        rel = src.relative_to(MIRROR_DIR)
        dst = HIDDEN_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
        print(f"  {rel}")

    print(f"\nDone. {copied} files copied to .claude/")
    print("Claude Code skills and settings are now available.")
    print("The sync hook will keep them up to date automatically.")


if __name__ == "__main__":
    main()
