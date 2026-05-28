#!/usr/bin/env python3
"""
wikilink_hook.py — Post-tool hook for Write/Edit on .md files.

Triggered after Claude writes or edits a markdown file.
Compares wikilinks and tags in the file against the wikilink index,
auto-updates the index for resolvable items, and alerts Claude to
unresolved references and new entities that need attention.

Output: JSON to stdout (hookSpecificOutput format).
"""

import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAULT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = VAULT_ROOT / "scripts" / "wikilink-index.json"
LOG_PATH = VAULT_ROOT / "scripts" / "wikilink_hook.log"
CONTENT_FOLDERS = {"team", "projects", "people", "companies", "weeklys", "daily-briefs", "context"}
KNOWN_TAG_CATEGORIES = {"meeting/", "project/", "prep/", "role/", "company/"}
WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_error(msg: str) -> None:
    """Append error message to log file. Never raises."""
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def parse_tool_input() -> str | None:
    """Read stdin JSON, extract file_path from tool_input. Returns str|None."""
    try:
        raw = sys.stdin.read()
        if not raw or not raw.strip():
            return None
        data = json.loads(raw)
        tool_input = data.get("tool_input", {})
        if isinstance(tool_input, str):
            try:
                tool_input = json.loads(tool_input)
            except json.JSONDecodeError:
                return None
        if not isinstance(tool_input, dict):
            return None
        file_path = tool_input.get("file_path")
        if not file_path:
            return None
        return str(file_path)
    except Exception as e:
        log_error(f"parse_tool_input error: {e}")
        return None


# ---------------------------------------------------------------------------
# Scope check
# ---------------------------------------------------------------------------

def is_in_scope(filepath: str) -> bool:
    """Check if file is .md and inside a content folder."""
    try:
        p = Path(filepath)
        if p.suffix.lower() != ".md":
            return False
        # Resolve to absolute so we can compare with VAULT_ROOT
        # Try to make it absolute relative to vault root if not already
        if not p.is_absolute():
            p = VAULT_ROOT / p
        # Get relative path from vault root
        try:
            rel = p.relative_to(VAULT_ROOT)
        except ValueError:
            return False
        # First part of the relative path must be a content folder
        parts = rel.parts
        if not parts:
            return False
        return parts[0] in CONTENT_FOLDERS
    except Exception as e:
        log_error(f"is_in_scope error for '{filepath}': {e}")
        return False


# ---------------------------------------------------------------------------
# Index I/O
# ---------------------------------------------------------------------------

def load_index() -> dict | None:
    """Read wikilink-index.json. Return dict or None on error."""
    try:
        if not INDEX_PATH.exists():
            return None
        text = INDEX_PATH.read_text(encoding="utf-8")
        return json.loads(text)
    except Exception as e:
        log_error(f"load_index error: {e}")
        return None


def save_index(index: dict) -> None:
    """Write updated index, updating last_updated timestamp."""
    try:
        index["last_updated"] = datetime.now(timezone.utc).isoformat()
        INDEX_PATH.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        log_error(f"save_index error: {e}")


# ---------------------------------------------------------------------------
# Frontmatter / content extraction
# ---------------------------------------------------------------------------

def extract_frontmatter(content: str) -> dict:
    """Simple YAML parser — same logic as seed script's parse_frontmatter
    but takes content string instead of filepath."""
    result = {}
    if not content.startswith("---"):
        return result

    end = content.find("\n---", 3)
    if end == -1:
        return result

    block = content[3:end].strip()
    lines = block.splitlines()

    current_key = None
    current_list = None
    skip_nested = False
    nested_indent = 0

    SKIP_KEYS = {"skills", "items"}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        if skip_nested:
            if indent > nested_indent or stripped.startswith("-"):
                continue
            else:
                skip_nested = False
                current_list = None
                current_key = None

        if stripped.startswith("- ") and current_list is not None:
            val = stripped[2:].strip().strip('"').strip("'")
            current_list.append(val)
            continue

        if stripped == "-" and current_list is not None:
            continue

        match = re.match(r'^([A-Za-z0-9_]+)\s*:\s*(.*)', stripped)
        if match:
            key = match.group(1)
            raw_val = match.group(2).strip()

            if key in SKIP_KEYS:
                current_key = key
                current_list = None
                skip_nested = True
                nested_indent = indent
                continue

            if raw_val == "" or raw_val is None:
                current_key = key
                current_list = []
                result[key] = current_list
                skip_nested = False
            elif raw_val in ("[]", "{}"):
                current_key = key
                current_list = None
                skip_nested = False
                result[key] = []
            else:
                current_key = key
                current_list = None
                skip_nested = False
                val = raw_val.strip('"').strip("'")
                result[key] = val

    return result


def extract_wikilinks(content: str) -> set:
    """Extract all unique canonical wikilink names from content.

    Pattern: [[Canonical Name]] or [[Canonical Name|Display Text]]
    Also handles Obsidian escape: [[Name\\|Alias]] — strip trailing backslash.
    Returns the canonical part (before |) as a set of strings.
    """
    raw = WIKILINK_RE.findall(content)
    # Strip trailing backslashes (Obsidian escape before pipe: [[Name\|Alias]])
    return {name.rstrip("\\").strip() for name in raw if name.rstrip("\\").strip()}


def extract_tags(content: str) -> list:
    """Extract tags list from frontmatter."""
    fm = extract_frontmatter(content)
    raw_tags = fm.get("tags", [])
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    return [t.strip() for t in raw_tags if t.strip()]


# ---------------------------------------------------------------------------
# Vault file lookup
# ---------------------------------------------------------------------------

def file_exists_in_vault(name: str) -> Path | None:
    """Search content folders for <name>.md. Returns Path|None."""
    target = f"{name}.md"
    for folder_name in CONTENT_FOLDERS:
        folder = VAULT_ROOT / folder_name
        if not folder.exists():
            continue
        # Search recursively
        for p in folder.rglob("*.md"):
            if p.name == target:
                return p
    return None


# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------

def infer_type_from_path(filepath: str) -> str:
    """Infer entry type from folder path."""
    try:
        p = Path(filepath)
        if not p.is_absolute():
            p = VAULT_ROOT / p
        try:
            rel = p.relative_to(VAULT_ROOT)
        except ValueError:
            return "context"
        parts = rel.parts
        if not parts:
            return "context"

        top = parts[0]
        if top == "team":
            # team/member/meetings/... -> meeting
            if "meetings" in parts:
                return "meeting"
            return "person"
        elif top == "people":
            return "person"
        elif top == "projects":
            if "meetings" in parts:
                return "meeting"
            return "project"
        elif top == "companies":
            return "company"
        elif top == "weeklys":
            return "meeting"
        elif top == "daily-briefs":
            return "daily-brief"
        elif top == "context":
            return "context"
        else:
            return "context"
    except Exception as e:
        log_error(f"infer_type_from_path error for '{filepath}': {e}")
        return "context"


# ---------------------------------------------------------------------------
# Alias lookup helper
# ---------------------------------------------------------------------------

def _build_alias_map(wikilinks_index: dict) -> dict:
    """Build case-insensitive alias -> canonical map from index."""
    alias_map = {}
    for canonical, entry in wikilinks_index.items():
        alias_map[canonical.lower()] = canonical
        for alias in entry.get("aliases", []):
            alias_map[alias.lower()] = canonical
    return alias_map


# ---------------------------------------------------------------------------
# Core compare-and-update logic
# ---------------------------------------------------------------------------

def compare_and_update(
    wikilinks: set,
    tags: list,
    index: dict,
) -> tuple[list, list, bool]:
    """Compare extracted items against index.

    Returns:
        actions: list of str (items auto-added)
        alerts: list of str (items needing Claude review)
        index_changed: bool
    """
    actions = []
    alerts = []
    index_changed = False

    wikilinks_index: dict = index.get("wikilinks", {})
    tags_index: dict = index.get("tags", {})
    taxonomy_set = set(tags_index.get("taxonomy", []))
    project_tags_set = set(tags_index.get("project_tags", []))

    alias_map = _build_alias_map(wikilinks_index)

    # --- Wikilinks ---
    for name in sorted(wikilinks):
        name_stripped = name.strip()
        if not name_stripped:
            continue

        # 1. Direct canonical match
        if name_stripped in wikilinks_index:
            continue

        # 2. Alias match (case-insensitive)
        if name_stripped.lower() in alias_map:
            continue

        # 3. Not in index — search vault
        found_path = file_exists_in_vault(name_stripped)
        if found_path is not None:
            # Auto-add to index
            file_rel = found_path.relative_to(VAULT_ROOT).as_posix()
            entry_type = infer_type_from_path(str(found_path))
            # Read aliases from frontmatter
            try:
                file_content = found_path.read_text(encoding="utf-8", errors="replace")
                fm = extract_frontmatter(file_content)
                raw_aliases = fm.get("aliases", [])
                if isinstance(raw_aliases, str):
                    raw_aliases = [raw_aliases]
                aliases = [a.strip() for a in raw_aliases if a.strip()]
            except Exception:
                aliases = []

            wikilinks_index[name_stripped] = {
                "file": file_rel,
                "aliases": aliases,
                "type": entry_type,
            }
            # Update alias map
            alias_map[name_stripped.lower()] = name_stripped
            for a in aliases:
                alias_map[a.lower()] = name_stripped

            index_changed = True
            actions.append(f'wikilink: "{name_stripped}" (arquivo encontrado: {file_rel})')
        else:
            # Not found anywhere — alert
            alerts.append(f'"{name_stripped}" — não há arquivo correspondente no vault')

    # --- Tags ---
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue

        # 1. In taxonomy or project_tags?
        if tag in taxonomy_set or tag in project_tags_set:
            continue

        # 2. Has known category prefix?
        matched_category = False
        for prefix in KNOWN_TAG_CATEGORIES:
            if tag.startswith(prefix):
                matched_category = True
                break

        if matched_category:
            # Auto-add to appropriate set
            if tag.startswith("project/") and tag not in {"project/active", "project/completed"}:
                project_tags_set.add(tag)
                tags_index["project_tags"] = sorted(project_tags_set)
            else:
                taxonomy_set.add(tag)
                tags_index["taxonomy"] = sorted(taxonomy_set)
            index_changed = True
            actions.append(f'tag: "{tag}" (padrão válido)')
        else:
            # Unknown tag
            alerts.append(f'"{tag}" — fora da taxonomia conhecida')

    return actions, alerts, index_changed


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def build_terms_list(index: dict) -> str:
    """Compact sorted string of all known terms (canonical names + aliases)."""
    terms = set()
    for canonical, entry in index.get("wikilinks", {}).items():
        terms.add(canonical)
        for alias in entry.get("aliases", []):
            terms.add(alias)
    return ", ".join(sorted(terms))


def format_output(
    filepath: str,
    actions: list,
    alerts: list,
    index: dict,
    file_content: str,
) -> str:
    """Build the additionalContext string."""
    try:
        rel_path = Path(filepath).relative_to(VAULT_ROOT).as_posix()
    except ValueError:
        rel_path = filepath

    lines = [f"[wikilink-hook] Arquivo: {rel_path}", ""]

    if actions:
        lines.append("✅ Adicionado ao índice:")
        for a in actions:
            lines.append(f"  - {a}")
        lines.append("")

    if alerts:
        wikilink_alerts = [a for a in alerts if a.startswith('"') and "não há arquivo" in a]
        tag_alerts = [a for a in alerts if "fora da taxonomia" in a]

        if wikilink_alerts:
            lines.append("⚠️ Wikilink não resolvido:")
            for a in wikilink_alerts:
                lines.append(f"  - {a}")
            lines.append("")

        if tag_alerts:
            lines.append("⚠️ Tag desconhecida:")
            for a in tag_alerts:
                lines.append(f"  - {a}")
            lines.append("")

    lines.append("📋 Revisão Claude pendente:")
    terms = build_terms_list(index)
    lines.append(f"Termos conhecidos no índice: {terms}")
    lines.append("")
    lines.append("Conteúdo do arquivo para análise semântica:")
    lines.append("---")
    lines.append(file_content)
    lines.append("---")
    lines.append("")
    lines.append("Instruções para Claude:")
    lines.append("1. Revise o conteúdo acima e identifique menções de entidades conhecidas que deveriam ser wikilinks")
    lines.append("2. Identifique entidades NOVAS (pessoas, empresas, projetos) mencionadas no texto que não existem no índice")
    lines.append("3. Para novas entidades: crie entries no índice JSON e, se houver contexto suficiente, crie o documento correspondente")
    lines.append("4. Para menções soltas de entidades conhecidas: aplique os wikilinks corretos no arquivo")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Orchestrate: parse input → scope check → load index → read file
    → extract → compare → save if changed → output JSON."""
    try:
        # 1. Parse input
        filepath = parse_tool_input()
        if filepath is None:
            print("{}")
            return

        # 2. Scope check
        if not is_in_scope(filepath):
            print("{}")
            return

        # 3. Load index
        index = load_index()
        if index is None:
            print("{}")
            return

        # 4. Read file content
        try:
            p = Path(filepath)
            if not p.is_absolute():
                p = VAULT_ROOT / p
            file_content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            log_error(f"read file error for '{filepath}': {e}")
            print("{}")
            return

        # 5. Extract wikilinks and tags
        wikilinks = extract_wikilinks(file_content)
        tags = extract_tags(file_content)

        # 6. Compare and update
        actions, alerts, index_changed = compare_and_update(wikilinks, tags, index)

        # 7. Save index if changed
        if index_changed:
            save_index(index)

        # 8. Silent when nothing to report
        if not actions and not alerts:
            print("{}")
            return

        # 9. Format output
        additional_context = format_output(filepath, actions, alerts, index, file_content)

        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": additional_context,
            }
        }
        # Use ensure_ascii=True to avoid encoding issues on Windows (cp1252 stdout)
        sys.stdout.buffer.write(
            (json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8")
        )

    except Exception as e:
        log_error(f"main() unhandled error: {e}\n{traceback.format_exc()}")
        print("{}")


if __name__ == "__main__":
    main()
