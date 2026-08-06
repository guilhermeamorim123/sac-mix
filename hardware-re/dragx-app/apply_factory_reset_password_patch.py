"""
Changes the vendor's hardcoded factory-reset confirmation password
("2323") to a password the owner actually knows (5656), inside
RestartShutdownActivity.smali's r(Ljava/lang/String;)V method -- the
InputDialog callback for the "Restore Factory" button already built
into the vendor's own Settings screen. Reuses their existing,
already-working reset logic (b.b.a.a.l.d.X0(this)) untouched -- only
the string comparison target changes.

Run once against decoded_newpkg's RestartShutdownActivity.smali:
    python apply_factory_reset_password_patch.py \
        decoded_newpkg/smali/cn/upus/app/upprinting/dragx/ui/activity/setting/RestartShutdownActivity.smali
"""
import sys

MARKER = (
    ".method public synthetic r(Ljava/lang/String;)V\n"
    "    .locals 1\n"
    "\n"
    '    const-string v0, "2323"\n'
)

REPLACEMENT = (
    ".method public synthetic r(Ljava/lang/String;)V\n"
    "    .locals 1\n"
    "\n"
    '    const-string v0, "5656"\n'
)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python apply_factory_reset_password_patch.py <path/to/RestartShutdownActivity.smali>")
    path = sys.argv[1]

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    occurrences = content.count(MARKER)
    if occurrences != 1:
        raise SystemExit(
            f"Expected exactly 1 occurrence of the r() method marker, found {occurrences}. "
            "Refusing to patch -- this file doesn't match what this script expects."
        )

    content = content.replace(MARKER, REPLACEMENT, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}: factory-reset confirmation password changed to 5656")


if __name__ == "__main__":
    main()
