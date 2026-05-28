#!/usr/bin/env python3
"""Remove ![[Recording*.m4a]] audio embed wikilinks from CLAUDE.md.

These are accidentally dropped at the top of CLAUDE.md when you attach
audio in Obsidian. Runs on SessionStart to keep the file clean.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PATTERN = re.compile(r"^\s*!\[\[Recording[^\]]*\.m4a\]\]\s*$", re.IGNORECASE)


def clean_file(path: Path) -> int:
    if not path.exists():
        return 0
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    cleaned = [line for line in lines if not PATTERN.match(line)]
    while cleaned and cleaned[0].strip() == "":
        cleaned.pop(0)
    new_content = "".join(cleaned)
    if new_content != original:
        path.write_text(new_content, encoding="utf-8")
        return len(lines) - len(cleaned)
    return 0


TARGETS = ("CLAUDE.md", "_claude/CLAUDE.md")


def main() -> int:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return 0
    root = Path(project_dir)
    for rel in TARGETS:
        clean_file(root / rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
