"""Shared utilities for vendor-path rewriting + vault-root discovery.

Used by both render_slides.py (at render time) and build_preview.py (at
preview-cache materialization time) so the two pipelines agree on:
  - What counts as a `/vendor/...` path
  - How to resolve it to an absolute file:// URL
  - How to find the vault root from any path inside the vault
"""
from __future__ import annotations

import re
from pathlib import Path

# Matches src="/vendor/X" or src='/vendor/X' (and href=). Capturing the
# matched quote so the rewrite preserves it (some HTML parsers care).
VENDOR_PATH_RE = re.compile(r'(src|href)=(["\'])(/vendor/[^"\']+)\2')


def find_vault_root(start: Path, *, fallback_levels: int = 4) -> Path:
    """Walk up from start until we find vendor/ or .git/ — that's vault root.

    If neither is found within 8 levels (or the filesystem root is hit),
    fall back to walking up `fallback_levels` directories from start.

    The fallback differs by caller:
      - render_slides.py passes a slide HTML path
        (vault/projects/<slug>/presentations/<deck>/slides/<file>.html) →
        4 levels up gets to vault.
      - build_preview.py passes a deck dir
        (vault/projects/<slug>/presentations/<deck>) →
        3 levels up gets to vault.
    """
    cur = start.resolve()
    for _ in range(8):
        if (cur / "vendor").is_dir() or (cur / ".git").exists():
            return cur
        if cur == cur.parent:
            break
        cur = cur.parent
    fallback = start.resolve()
    for _ in range(fallback_levels):
        fallback = fallback.parent
    return fallback


def rewrite_vendor_paths(html_str: str, vault_root: Path) -> tuple[str, bool]:
    """Rewrite `/vendor/...` paths to absolute file:// URLs.

    Returns (preprocessed_html, has_vendor_script). When the slide does not
    reference `/vendor/`, the input is returned untouched and `has_vendor=False`.
    This guarantees backward compatibility for legacy decks.

    Rationale: file:// URLs do not resolve absolute paths (`/vendor/X`) against
    `<base href>`. They resolve against the filesystem root. So we explicitly
    rewrite `/vendor/X` to `file:///<vault-root>/vendor/X`. No `<base href>` is
    injected because it would clobber relative paths like `../design-system.css`
    that the slide depends on.
    """
    if "/vendor/" not in html_str:
        return html_str, False
    vault_abs = str(vault_root.resolve())

    def _rewrite(m: re.Match) -> str:
        attr, quote, path = m.group(1), m.group(2), m.group(3)
        return f'{attr}={quote}file://{vault_abs}{path}{quote}'

    return VENDOR_PATH_RE.sub(_rewrite, html_str), True
