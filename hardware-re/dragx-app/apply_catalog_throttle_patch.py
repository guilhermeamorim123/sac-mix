"""
Removes the 180-second per-category request throttle (b.b.a.a.l.h.b(id),
"RequestIntervalUtil") from the app's catalog-fetch methods, so reopening
a category/brand/model screen always attempts a fresh network fetch
instead of silently skipping it. See
docs/superpowers/specs/2026-07-06-catalog-refresh-design.md for the full
root-cause writeup. This does NOT touch the existing local-cache-first /
reconcile-on-response logic elsewhere in the app -- only removes an
artificial delay on the fetch attempt itself.

Run once against a freshly-decoded (never-patched) d.smali:
    python apply_catalog_throttle_patch.py path/to/d.smali
"""
import re
import sys

# Matches the call to the throttle check, the move-result, and the
# following if-eqz branch -- captures the target label so we can replace
# just the if-eqz line with an unconditional goto to that same label.
PATTERN = re.compile(
    r"(invoke-static \{[^}]*\}, Lb/b/a/a/l/h;->b\(Ljava/lang/String;\)Z\n"
    r"\n"
    r"    move-result v0\n"
    r"\n"
    r"    )if-eqz v0, (:cond_\d+)\n"
)


def main():
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = list(PATTERN.finditer(content))
    if len(matches) != 4:
        raise SystemExit(
            f"Expected exactly 4 throttle-check call sites, found {len(matches)}. "
            "Refusing to patch -- this file doesn't match what this script expects."
        )

    def replace(m):
        return f"{m.group(1)}goto/16 {m.group(2)}\n"

    new_content = PATTERN.sub(replace, content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Patched {path}: neutralized 4 throttle-check call sites (if-eqz -> goto/16).")


if __name__ == "__main__":
    main()
