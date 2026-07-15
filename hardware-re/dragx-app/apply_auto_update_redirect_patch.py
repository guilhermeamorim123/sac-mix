"""
Redirects ONLY the `.b()` Retrofit client's base URL (used by app_upgrade,
find_all_data, and user_themes -- see
docs/superpowers/specs/2026-07-07-dragx-auto-update-design.md) to the fleet
panel, leaving the `.a()` client (catalog fetches, everything else)
pointed at the real vendor server. Both clients share a single string
constant in the decompiled source, so this works by inserting a NEW
const-string that overwrites the shared register immediately before its
one use inside the `.b()`-building branch (:cond_0), which is unreachable
from the `.a()`-building branch (it returns first via a `goto`).

Run once against a freshly-decoded (never-patched) b.smali:
    python apply_auto_update_redirect_patch.py path/to/b.smali <fleet-panel-base-url>

Example:
    python apply_auto_update_redirect_patch.py decoded/smali/b/b/a/a/g/c/b.smali https://dragx-fleet-panel.onrender.com/v1/

Note: the URL MUST end in a trailing slash. Retrofit.Builder.baseUrl()
(Li/u$b;->a(Ljava/lang/String;)) throws IllegalArgumentException at
runtime -- uncaught, on every cold start -- if the last path segment
isn't empty. The vendor's own original constant
("http://cutter.skycut.cn/v1/") follows this rule; match it.
"""
import sys

MARKER = (
    "    .line 11\n"
    "    :cond_0\n"
    "    new-instance v4, Li/u$b;\n"
    "\n"
    "    invoke-direct {v4}, Li/u$b;-><init>()V\n"
    "\n"
    "    .line 12\n"
    "    invoke-virtual {v4, v2}, Li/u$b;->a(Ljava/lang/String;)Li/u$b;\n"
)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python apply_auto_update_redirect_patch.py <path/to/b.smali> <fleet-panel-base-url>")
    path = sys.argv[1]
    fleet_panel_url = sys.argv[2]

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    occurrences = content.count(MARKER)
    if occurrences != 1:
        raise SystemExit(
            f"Expected exactly 1 occurrence of the :cond_0 marker, found {occurrences}. "
            "Refusing to patch -- this file doesn't match what this script expects."
        )

    insertion = (
        "    .line 11\n"
        "    :cond_0\n"
        f'    const-string v2, "{fleet_panel_url}"\n'
        "\n"
        "    new-instance v4, Li/u$b;\n"
        "\n"
        "    invoke-direct {v4}, Li/u$b;-><init>()V\n"
        "\n"
        "    .line 12\n"
        "    invoke-virtual {v4, v2}, Li/u$b;->a(Ljava/lang/String;)Li/u$b;\n"
    )
    content = content.replace(MARKER, insertion, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}: .b() client now points at {fleet_panel_url}")


if __name__ == "__main__":
    main()
