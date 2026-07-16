"""
v724-baseline equivalent of the credit/expiry gate removal already applied
to decoded/ and decoded_repackaged/ (see README.md's "Credit gate removed"
section). Traced 2026-07-16 against decoded_v724/, confirmed live/blocking
on real hardware (balance showed "-5", "Balance run out, please recharge!").

Two files, two sites each, all four converging on a single label per file
that leads straight into the real cut-proceed call:

- FilmCutActivity.smali, method T1(): both sites converge on :cond_8
  (-> R1(), the actual cut).
- CustomCutActivity.smali, method R0(): both sites converge on :cond_5
  (-> P0(), the actual cut).

Each site is a dead `cmp-long` (left in place, matching the exact pattern
already used in decoded/'s pre-patched copies) followed by `if-gez vN,
:cond_N` -- changed to an unconditional `goto/16 :cond_N`, so the
low-balance/expired branch (blocking toast + return-void) is never taken.
Only the gate is removed; the balance/quantity display and decrement
bookkeeping elsewhere are untouched, matching the original v705 patch's
documented scope.

Run once against freshly-decoded (never-patched) files:
    python apply_credit_gate_patch_v724.py decoded_v724/smali/cn/upus/app/upprinting/ui/activity/FilmCutActivity.smali
    python apply_credit_gate_patch_v724.py decoded_v724/smali/cn/upus/app/upprinting/ui/activity/CustomCutActivity.smali
"""
import sys

# (marker, replacement, label) pairs, keyed by which file they apply to.
PATCHES_BY_FILE = {
    "FilmCutActivity.smali": [
        (
            "    cmp-long v4, v0, v2\n\n    if-gez v4, :cond_8\n",
            "    cmp-long v4, v0, v2\n\n    goto/16 :cond_8\n",
            "Site 1 (balance check -> :cond_8)",
        ),
        (
            "    :cond_7\n    cmp-long v2, v0, v6\n\n    if-gez v2, :cond_8\n",
            "    :cond_7\n    cmp-long v2, v0, v6\n\n    goto/16 :cond_8\n",
            "Site 2 (expiry check -> :cond_8)",
        ),
    ],
    "CustomCutActivity.smali": [
        (
            "    cmp-long v4, v0, v2\n\n    if-gez v4, :cond_5\n",
            "    cmp-long v4, v0, v2\n\n    goto/16 :cond_5\n",
            "Site 1 (balance check -> :cond_5)",
        ),
        (
            "    :cond_4\n    cmp-long v2, v0, v6\n\n    if-gez v2, :cond_5\n",
            "    :cond_4\n    cmp-long v2, v0, v6\n\n    goto/16 :cond_5\n",
            "Site 2 (expiry check -> :cond_5)",
        ),
    ],
}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python apply_credit_gate_patch_v724.py <path/to/FilmCutActivity.smali or CustomCutActivity.smali>")
    path = sys.argv[1]

    basename = None
    for name in PATCHES_BY_FILE:
        if path.replace("\\", "/").endswith(name):
            basename = name
            break
    if basename is None:
        raise SystemExit(f"Don't know the patch markers for {path} -- expected it to end in FilmCutActivity.smali or CustomCutActivity.smali")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    for marker, replacement, label in PATCHES_BY_FILE[basename]:
        occurrences = content.count(marker)
        if occurrences != 1:
            raise SystemExit(
                f"{label}: expected exactly 1 occurrence of the marker, found {occurrences}. "
                "Refusing to patch -- this file doesn't match what this script expects."
            )
        content = content.replace(marker, replacement, 1)
        print(f"OK: {label} patched in {path}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
