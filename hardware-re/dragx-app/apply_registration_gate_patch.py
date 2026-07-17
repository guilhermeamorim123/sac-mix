"""
Replaces InitActivity.p(Context)'s body -- previously "construct an Intent
for InitActivity itself and start it" -- with a single delegating call to
RegistrationGate.launchNextScreen(Context), the new class added in
Task 2/4 of docs/superpowers/plans/2026-07-16-customer-registration-app-plan.md.
RegistrationGate decides whether to proceed to the real InitActivity (if
already approved) or show the registration/waiting screen instead, and
starts the background status poller either way.

This is the ONLY call site that needs patching: StartActivity calls
InitActivity.p(Context) from exactly two places (confirmed by reading the
decompile), both immediately followed by finish() on the caller -- so
gating this one static method gates the app's entire entry point,
regardless of which of StartActivity's two call sites fires.

Run once against a freshly-decoded (never-patched) InitActivity.smali:
    python apply_registration_gate_patch.py path/to/InitActivity.smali
"""
import sys

MARKER = (
    ".method public static p(Landroid/content/Context;)V\n"
    "    .locals 2\n"
    "\n"
    "    .line 1\n"
    "    new-instance v0, Landroid/content/Intent;\n"
    "\n"
    "    const-class v1, Lcn/upus/app/upprinting/dragx/ui/activity/InitActivity;\n"
    "\n"
    "    invoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V\n"
    "\n"
    "    .line 2\n"
    "    invoke-virtual {p0, v0}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V\n"
    "\n"
    "    return-void\n"
    ".end method\n"
)

REPLACEMENT = (
    ".method public static p(Landroid/content/Context;)V\n"
    "    .locals 0\n"
    "\n"
    "    invoke-static {p0}, Lcn/upus/app/upprinting/dragx/ui/activity/RegistrationGate;->launchNextScreen(Landroid/content/Context;)V\n"
    "\n"
    "    return-void\n"
    ".end method\n"
)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python apply_registration_gate_patch.py <path/to/InitActivity.smali>")
    path = sys.argv[1]

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    occurrences = content.count(MARKER)
    if occurrences != 1:
        raise SystemExit(
            f"Expected exactly 1 occurrence of the p(Context) marker, found {occurrences}. "
            "Refusing to patch -- this file doesn't match what this script expects."
        )

    content = content.replace(MARKER, REPLACEMENT, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}: InitActivity.p(Context) now delegates to RegistrationGate.launchNextScreen(Context)")


if __name__ == "__main__":
    main()
