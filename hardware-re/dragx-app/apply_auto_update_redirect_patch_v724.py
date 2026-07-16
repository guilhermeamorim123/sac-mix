"""
v724-baseline equivalent of apply_auto_update_redirect_patch.py.

The v705 decompile (decoded/) and the v724 decompile (decoded_v724/) have
completely different obfuscated class layouts for the same feature -- the
dual-Retrofit-client pattern that was in `b/b/a/a/g/c/b.smali` (method
`e(Z)V`) in v705 lives in `b/b/a/a/o/c/e.smali` (method `f(ZJ)V`) in v724.
Traced via a dedicated Explore pass on 2026-07-16 (see chat history) --
confirmed the no-interceptor client (field `b`, built in the `:cond_0`
branch here) is used by EXACTLY three endpoints in the whole v724 app:
app_upgrade, find_all_data, and user_themes -- the same three as v705's
`.b()`/f99b client. The interceptor-bearing client (field `a`, ~54 call
sites across the app, catalog fetches included) is built in the other
branch, which completes and returns via `goto :goto_0` before `:cond_0`
is ever reached -- structurally unreachable from this insertion, exactly
like the v705 case.

Run once against a freshly-decoded (never-patched) e.smali:
    python apply_auto_update_redirect_patch_v724.py path/to/e.smali <fleet-panel-base-url>

Example (URL MUST end in / -- Retrofit's baseUrl() throws otherwise, see
the trailing-slash bug fixed in the v705 patch on 2026-07-16):
    python apply_auto_update_redirect_patch_v724.py decoded_v724/smali/b/b/a/a/o/c/e.smali https://dragx-fleet-panel.onrender.com/v1/
"""
import sys

MARKER = (
    "    .line 10\n"
    "    :cond_0\n"
    "    new-instance v2, Li/u$b;\n"
    "\n"
    "    invoke-direct {v2}, Li/u$b;-><init>()V\n"
    "\n"
    "    .line 11\n"
    "    invoke-virtual {v2, v0}, Li/u$b;->a(Ljava/lang/String;)Li/u$b;\n"
)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python apply_auto_update_redirect_patch_v724.py <path/to/e.smali> <fleet-panel-base-url>")
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
        "    .line 10\n"
        "    :cond_0\n"
        f'    const-string v0, "{fleet_panel_url}"\n'
        "\n"
        "    new-instance v2, Li/u$b;\n"
        "\n"
        "    invoke-direct {v2}, Li/u$b;-><init>()V\n"
        "\n"
        "    .line 11\n"
        "    invoke-virtual {v2, v0}, Li/u$b;->a(Ljava/lang/String;)Li/u$b;\n"
    )
    content = content.replace(MARKER, insertion, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}: .c() client (app_upgrade/find_all_data/user_themes) now points at {fleet_panel_url}")


if __name__ == "__main__":
    main()
