"""Sync Observable Plot + Mermaid vendor libs to vendor/.

Versions are pinned constants. SHA256 hashes are pinned constants too —
download is only accepted if hash matches. To bump a version:
  1. Edit URL constant for the lib
  2. Set its SHA256 to "SHA256_TBD_BOOTSTRAP"
  3. Run `python3 scripts/sync_vendor_libs.py --bootstrap` to print the hash
  4. Paste the printed hash into the constant
  5. Run normally to validate

CLI:
  python3 scripts/sync_vendor_libs.py             # download + validate
  python3 scripts/sync_vendor_libs.py --check-only  # validate vendor/ without downloading
  python3 scripts/sync_vendor_libs.py --bootstrap   # download + print SHA256 (no validation)

Exit codes:
  0  success
  1  SHA256 mismatch / missing file in --check-only
  2  download failed
  64 usage

macOS CA bundle gotcha:
  Python from python.org may ship without an activated CA bundle, causing
  CERTIFICATE_VERIFY_FAILED on download. One-time fix:
    /Applications/Python\\ 3.13/Install\\ Certificates.command
  Or per-run workaround:
    SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/sync_vendor_libs.py
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DEST = Path("vendor")


@dataclass(frozen=True)
class VendorLib:
    filename: str
    version: str
    url: str
    sha256: str


# Pinned versions + hashes. To bump: see module docstring.
# Task 2 (Bootstrap) will replace "SHA256_TBD_BOOTSTRAP" with the real hashes.
LIBS: tuple[VendorLib, ...] = (
    VendorLib(
        filename="d3.min.js",
        version="7.9.0",
        url="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js",
        sha256="f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539",
    ),
    VendorLib(
        filename="plot.umd.min.js",
        version="0.6.17",
        url="https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/dist/plot.umd.min.js",
        sha256="4358086467740777dd788d6b27a95cebdbaefdd50c730a3060117073bd7134cb",
    ),
    VendorLib(
        filename="mermaid.min.js",
        version="11.4.1",
        url="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js",
        sha256="a43bc1afd446f9c4cc66ac5dd45d02e8d65e26fc5344ec0ef787f88d6ddb6f9e",
    ),
    VendorLib(
        filename="lucide.min.js",
        version="0.469.0",
        url="https://cdn.jsdelivr.net/npm/lucide@0.469.0/dist/umd/lucide.min.js",
        sha256="5de4fffddc1b41ad1226d5e986fcc552adb8ad9efd1566e71dfdcdb664f9a6c2",
    ),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync vendor libs (Plot + Mermaid) to vendor/.",
    )
    parser.add_argument(
        "--dest", type=Path, default=DEFAULT_DEST,
        help="Destination directory (default: vendor/).",
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Validate existing vendor/ files against pinned SHA256; no download.",
    )
    parser.add_argument(
        "--bootstrap", action="store_true",
        help="Download + print SHA256 of received content; skip hash validation.",
    )
    return parser.parse_args(argv)


def _sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str) -> bytes:
    """Fetch URL contents. Raises urllib.error.URLError on network failure."""
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def check_only(dest: Path) -> int:
    """Validate that every pinned lib exists in dest with matching SHA256.

    Returns 0 if all good, 1 otherwise.
    """
    failed = False
    for lib in LIBS:
        path = dest / lib.filename
        if not path.is_file():
            print(f"missing: {path}", file=sys.stderr)
            failed = True
            continue
        actual = _sha256_of(path.read_bytes())
        if actual != lib.sha256:
            print(
                f"sha256 mismatch for {lib.filename}: "
                f"got {actual}, expected {lib.sha256}",
                file=sys.stderr,
            )
            failed = True
    return 1 if failed else 0


def sync(dest: Path, bootstrap: bool) -> int:
    """Download every pinned lib + validate. Returns 0 on success."""
    dest.mkdir(parents=True, exist_ok=True)
    bootstrap_hashes: dict[str, str] = {}
    for lib in LIBS:
        try:
            data = _download(lib.url)
        except urllib.error.URLError as exc:
            print(f"download failed for {lib.filename}: {exc}", file=sys.stderr)
            return 2
        actual = _sha256_of(data)
        if bootstrap:
            bootstrap_hashes[lib.filename] = actual
        elif actual != lib.sha256:
            print(
                f"sha256 mismatch for {lib.filename}: got {actual}, "
                f"expected {lib.sha256}. Refusing to write.",
                file=sys.stderr,
            )
            return 1
        (dest / lib.filename).write_bytes(data)
        print(f"✓ {lib.filename} ({len(data):,} bytes, sha256={actual[:12]}…)")
    if bootstrap:
        print()
        print("Bootstrap mode — paste the following hashes into scripts/sync_vendor_libs.py:")
        for fname, h in bootstrap_hashes.items():
            print(f"  {fname}: {h}")
        return 0
    write_manifest(dest)
    return 0


def write_manifest(dest: Path) -> Path:
    """Write vendor/README.md with manifest of versions + hashes + timestamp."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = "\n".join(
        f"| `{lib.filename}` | {lib.version} | `{lib.sha256}` | <{lib.url}> |"
        for lib in LIBS
    )
    body = f"""# Vendor libs (read-only, sync-managed)

Bibliotecas baixadas via `scripts/sync_vendor_libs.py`. **Não edite manualmente.**
Versões e SHA256 são pinados no script — re-sync valida automaticamente.

- **Last sync:** `{timestamp}`
- **Source:** jsdelivr.net (URLs canônicas abaixo)

## Manifest

| File | Version | SHA256 | URL |
|------|---------|--------|-----|
{rows}

## Re-sync

```
python3 scripts/sync_vendor_libs.py            # download + validate
python3 scripts/sync_vendor_libs.py --check-only  # validate sem baixar
```

## Bump de versão

Veja o docstring de `scripts/sync_vendor_libs.py`.
"""
    out = dest / "README.md"
    out.write_text(body)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check_only:
        return check_only(args.dest)
    return sync(args.dest, bootstrap=args.bootstrap)


if __name__ == "__main__":
    raise SystemExit(main())
