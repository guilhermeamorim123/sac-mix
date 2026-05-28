#!/usr/bin/env python3
"""
seed_wikilink_index.py — Scan CoS Obsidian vault and generate wikilink-index.json.

Usage:
    python scripts/seed_wikilink_index.py            # Generate (skips if exists)
    python scripts/seed_wikilink_index.py --rebuild  # Force regenerate
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

VAULT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
INDEX_FILE = SCRIPTS_DIR / "wikilink-index.json"
INITIAL_COMPANIES_FILE = SCRIPTS_DIR / "initial-companies.json"

# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a .md file.

    Handles:
      - Flat key: value pairs (with or without quotes)
      - Lists (  - item)
      - Skips complex/nested blocks (skills:, items:, etc.)

    Returns an empty dict if no frontmatter found.
    """
    result = {}
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    # Must start with ---
    if not text.startswith("---"):
        return result

    # Find closing ---
    end = text.find("\n---", 3)
    if end == -1:
        return result

    block = text[3:end].strip()
    lines = block.splitlines()

    current_key = None
    current_list = None
    skip_nested = False
    nested_indent = 0

    # Keys whose values are complex nested objects — skip their content
    SKIP_KEYS = {"skills", "items"}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect indentation level
        indent = len(line) - len(line.lstrip())

        # If we are inside a nested block to skip, check if we've returned
        if skip_nested:
            if indent > nested_indent or stripped.startswith("-"):
                continue
            else:
                skip_nested = False
                current_list = None
                current_key = None

        # List item under current key
        if stripped.startswith("- ") and current_list is not None:
            val = stripped[2:].strip().strip('"').strip("'")
            current_list.append(val)
            continue

        # Bare list item (edge case)
        if stripped == "-" and current_list is not None:
            continue

        # Key: value line
        match = re.match(r'^([A-Za-z0-9_]+)\s*:\s*(.*)', stripped)
        if match:
            key = match.group(1)
            raw_val = match.group(2).strip()

            # If key should be skipped (nested complex object)
            if key in SKIP_KEYS:
                current_key = key
                current_list = None
                skip_nested = True
                nested_indent = indent
                continue

            if raw_val == "" or raw_val is None:
                # Start of a list or nested block
                current_key = key
                current_list = []
                result[key] = current_list
                skip_nested = False
            elif raw_val in ("[]", "{}"):
                # Explicit empty list/dict inline notation
                current_key = key
                current_list = None
                skip_nested = False
                result[key] = []
            else:
                current_key = key
                current_list = None
                skip_nested = False
                # Strip quotes
                val = raw_val.strip('"').strip("'")
                result[key] = val

    return result


# ---------------------------------------------------------------------------
# Helper: add entry to index
# ---------------------------------------------------------------------------

def add_entry(index: dict, canonical: str, file_rel: str | None,
              aliases: list, entry_type: str) -> None:
    """Add or merge a wikilink entry into the index dict."""
    if canonical not in index:
        index[canonical] = {
            "file": file_rel,
            "aliases": aliases,
            "type": entry_type,
        }
    else:
        # Merge aliases (avoid duplicates)
        existing = index[canonical]["aliases"]
        for a in aliases:
            if a not in existing:
                existing.append(a)


# ---------------------------------------------------------------------------
# Scan functions
# ---------------------------------------------------------------------------

def scan_persons(index: dict) -> None:
    """Scan team/*/ and people/ for person profiles (type=person)."""
    search_dirs = [
        VAULT_ROOT / "team",
        VAULT_ROOT / "people",
    ]
    for base in search_dirs:
        if not base.exists():
            continue
        if base.name == "team":
            # team/<member>/*.md — one level deep, not inside meetings/
            for md in base.rglob("*.md"):
                parts = md.relative_to(base).parts
                # Skip files inside meetings/ subdirectories or nested >2 levels
                if "meetings" in parts:
                    continue
                fm = parse_frontmatter(md)
                if fm.get("type") != "person":
                    continue
                canonical = md.stem
                name = fm.get("name", canonical)
                raw_aliases = fm.get("aliases", [])
                if isinstance(raw_aliases, str):
                    raw_aliases = [raw_aliases]
                aliases = list(raw_aliases)
                # Include the name itself as alias if different from canonical
                if name and name != canonical and name not in aliases:
                    aliases.insert(0, name)
                file_rel = md.relative_to(VAULT_ROOT).as_posix()
                add_entry(index, canonical, file_rel, aliases, "person")
        else:
            # people/*.md — flat directory
            for md in base.glob("*.md"):
                fm = parse_frontmatter(md)
                if fm.get("type") != "person":
                    continue
                canonical = md.stem
                name = fm.get("name", canonical)
                raw_aliases = fm.get("aliases", [])
                if isinstance(raw_aliases, str):
                    raw_aliases = [raw_aliases]
                aliases = list(raw_aliases)
                if name and name != canonical and name not in aliases:
                    aliases.insert(0, name)
                file_rel = md.relative_to(VAULT_ROOT).as_posix()
                add_entry(index, canonical, file_rel, aliases, "person")


def scan_projects(index: dict) -> None:
    """Scan projects/*/ for project context files (type=project)."""
    base = VAULT_ROOT / "projects"
    if not base.exists():
        return
    for md in base.rglob("*.md"):
        parts = md.relative_to(base).parts
        # Skip files inside meetings/ subdirectories
        if "meetings" in parts:
            continue
        fm = parse_frontmatter(md)
        if fm.get("type") != "project":
            continue
        canonical = md.stem
        name = fm.get("name", canonical)
        raw_aliases = fm.get("aliases", [])
        if isinstance(raw_aliases, str):
            raw_aliases = [raw_aliases]
        aliases = list(raw_aliases)
        if name and name != canonical and name not in aliases:
            aliases.insert(0, name)
        file_rel = md.relative_to(VAULT_ROOT).as_posix()
        add_entry(index, canonical, file_rel, aliases, "project")


def scan_companies(index: dict) -> None:
    """Scan companies/ for company docs, then merge initial-companies.json."""
    companies_dir = VAULT_ROOT / "companies"
    vault_companies: set[str] = set()

    if companies_dir.exists():
        for md in companies_dir.glob("*.md"):
            if md.name == ".gitkeep":
                continue
            fm = parse_frontmatter(md)
            canonical = md.stem
            name = fm.get("name", canonical)
            raw_aliases = fm.get("aliases", [])
            if isinstance(raw_aliases, str):
                raw_aliases = [raw_aliases]
            aliases = list(raw_aliases)
            if name and name != canonical and name not in aliases:
                aliases.insert(0, name)
            file_rel = md.relative_to(VAULT_ROOT).as_posix()
            add_entry(index, canonical, file_rel, aliases, "company")
            vault_companies.add(canonical)

    # Merge initial-companies.json — add entries not already in vault
    if INITIAL_COMPANIES_FILE.exists():
        try:
            raw = json.loads(INITIAL_COMPANIES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}
        for company_name, aliases_list in raw.items():
            canonical = company_name
            if canonical in vault_companies:
                continue
            if isinstance(aliases_list, str):
                aliases_list = [aliases_list]
            else:
                aliases_list = list(aliases_list)
            add_entry(index, canonical, None, aliases_list, "company")


def scan_meetings(index: dict) -> None:
    """Scan all meeting directories for meeting records (type=meeting)."""
    meeting_paths = []

    # team/*/meetings/YYYY-MM-DD/*.md
    team_base = VAULT_ROOT / "team"
    if team_base.exists():
        meeting_paths.extend(team_base.rglob("meetings/**/*.md"))

    # weeklys/YYYY-MM-DD/*.md
    weeklys_base = VAULT_ROOT / "weeklys"
    if weeklys_base.exists():
        meeting_paths.extend(weeklys_base.rglob("*.md"))

    # projects/*/meetings/YYYY-MM-DD/*.md
    projects_base = VAULT_ROOT / "projects"
    if projects_base.exists():
        for md in projects_base.rglob("meetings/**/*.md"):
            meeting_paths.append(md)

    seen = set()
    for md in meeting_paths:
        if md in seen:
            continue
        seen.add(md)
        if md.suffix != ".md":
            continue
        fm = parse_frontmatter(md)
        if fm.get("type") != "meeting":
            continue
        canonical = md.stem
        file_rel = md.relative_to(VAULT_ROOT).as_posix()
        add_entry(index, canonical, file_rel, [], "meeting")


def scan_context_files(index: dict) -> None:
    """Scan context/, root MOC files, and _Index.md."""
    # context/*.md
    context_dir = VAULT_ROOT / "context"
    if context_dir.exists():
        for md in context_dir.glob("*.md"):
            canonical = md.stem
            file_rel = md.relative_to(VAULT_ROOT).as_posix()
            add_entry(index, canonical, file_rel, [], "context")

    # Root-level MOC *.md
    for md in VAULT_ROOT.glob("MOC *.md"):
        canonical = md.stem
        file_rel = md.relative_to(VAULT_ROOT).as_posix()
        add_entry(index, canonical, file_rel, [], "context")

    # _Index.md
    index_file = VAULT_ROOT / "_Index.md"
    if index_file.exists():
        canonical = index_file.stem
        file_rel = index_file.relative_to(VAULT_ROOT).as_posix()
        add_entry(index, canonical, file_rel, [], "context")


# ---------------------------------------------------------------------------
# Tag scanning
# ---------------------------------------------------------------------------

FIXED_TAXONOMY = [
    "meeting/1on1",
    "meeting/weekly",
    "meeting/project",
    "project/active",
    "project/completed",
    "prep/1on1",
    "prep/weekly",
    "role/board",
    "role/direct-report",
    "role/external",
    "company/partner",
    "company/active",
    "context",
    "development",
    "decisions",
    "index",
    "daily-brief",
]

CONTENT_FOLDERS = [
    "team",
    "projects",
    "people",
    "companies",
    "weeklys",
    "daily-briefs",
    "context",
]


def scan_tags(index_tags: dict) -> None:
    """Scan all .md files in content folders for tags: in frontmatter."""
    taxonomy_set = set(FIXED_TAXONOMY)
    project_tags_set: set[str] = set()

    # Collect project/* tags that are NOT active/completed
    protected = {"project/active", "project/completed"}

    for folder_name in CONTENT_FOLDERS:
        folder = VAULT_ROOT / folder_name
        if not folder.exists():
            continue
        for md in folder.rglob("*.md"):
            fm = parse_frontmatter(md)
            raw_tags = fm.get("tags", [])
            if isinstance(raw_tags, str):
                raw_tags = [raw_tags]
            for tag in raw_tags:
                tag = tag.strip()
                if not tag:
                    continue
                if tag.startswith("project/") and tag not in protected:
                    project_tags_set.add(tag)
                else:
                    taxonomy_set.add(tag)

    # Also scan root-level MOC and _Index
    for md in VAULT_ROOT.glob("MOC *.md"):
        fm = parse_frontmatter(md)
        raw_tags = fm.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        for tag in raw_tags:
            tag = tag.strip()
            if tag:
                taxonomy_set.add(tag)

    index_md = VAULT_ROOT / "_Index.md"
    if index_md.exists():
        fm = parse_frontmatter(index_md)
        raw_tags = fm.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        for tag in raw_tags:
            tag = tag.strip()
            if tag:
                taxonomy_set.add(tag)

    index_tags["taxonomy"] = sorted(taxonomy_set)
    index_tags["project_tags"] = sorted(project_tags_set)


# ---------------------------------------------------------------------------
# Build index
# ---------------------------------------------------------------------------

def build_index() -> dict:
    """Orchestrate all scans and return the complete index dict."""
    wikilinks: dict = {}
    tags: dict = {}

    scan_persons(wikilinks)
    scan_projects(wikilinks)
    scan_companies(wikilinks)
    scan_meetings(wikilinks)
    scan_context_files(wikilinks)
    scan_tags(tags)

    return {
        "version": 1,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "wikilinks": wikilinks,
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rebuild = "--rebuild" in sys.argv

    if INDEX_FILE.exists() and not rebuild:
        print(f"Index already exists at {INDEX_FILE}.")
        print("Use --rebuild to regenerate.")
        return

    print("Building wikilink index...")
    index = build_index()

    INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    wikilink_count = len(index["wikilinks"])
    tag_count = len(index["tags"].get("taxonomy", []))
    project_tag_count = len(index["tags"].get("project_tags", []))
    print(f"Done. {wikilink_count} wikilinks, {tag_count} taxonomy tags, "
          f"{project_tag_count} project tags.")
    print(f"Index written to: {INDEX_FILE}")


if __name__ == "__main__":
    main()
