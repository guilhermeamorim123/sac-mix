"""
Wires SecretExitTapListener onto SettingActivity's "view1" -- an
existing, purely decorative invisible spacer view already in the
layout (flanks the data-version label at the bottom of the settings
list), so this adds no new visible UI element. Inserted right before
j()'s single return-void (confirmed the only exit point in this
method), using newly-bumped local register numbers so nothing already
in use gets clobbered.

Run once against decoded_newpkg's SettingActivity.smali:
    python apply_secret_exit_patch.py \
        decoded_newpkg/smali/cn/upus/app/upprinting/dragx/ui/activity/setting/SettingActivity.smali
"""
import sys

LOCALS_MARKER = (
    ".method public j()V\n"
    "    .locals 11\n"
)

LOCALS_REPLACEMENT = (
    ".method public j()V\n"
    "    .locals 15\n"
)

RETURN_MARKER = (
    "    :cond_6\n"
    "    :goto_2\n"
    "    return-void\n"
    ".end method\n"
)

RETURN_REPLACEMENT = (
    "    :cond_6\n"
    "    :goto_2\n"
    "    invoke-virtual {p0}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;\n"
    "\n"
    "    move-result-object v11\n"
    "\n"
    '    const-string v12, "tv_title"\n'
    "\n"
    '    const-string v13, "id"\n'
    "\n"
    "    invoke-virtual {p0}, Landroid/content/Context;->getPackageName()Ljava/lang/String;\n"
    "\n"
    "    move-result-object v14\n"
    "\n"
    "    invoke-virtual {v11, v12, v13, v14}, Landroid/content/res/Resources;->getIdentifier(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)I\n"
    "\n"
    "    move-result v11\n"
    "\n"
    "    invoke-virtual {p0, v11}, Landroid/app/Activity;->findViewById(I)Landroid/view/View;\n"
    "\n"
    "    move-result-object v11\n"
    "\n"
    "    new-instance v12, Lcn/upus/app/upprinting/dragx/ui/activity/SecretExitTapListener;\n"
    "\n"
    "    invoke-direct {v12, p0}, Lcn/upus/app/upprinting/dragx/ui/activity/SecretExitTapListener;-><init>(Landroid/app/Activity;)V\n"
    "\n"
    "    invoke-virtual {v11, v12}, Landroid/view/View;->setOnClickListener(Landroid/view/View$OnClickListener;)V\n"
    "\n"
    "    return-void\n"
    ".end method\n"
)


def apply_one(content, marker, replacement, label):
    occurrences = content.count(marker)
    if occurrences != 1:
        raise SystemExit(
            f"Expected exactly 1 occurrence of the {label} marker, found {occurrences}. "
            "Refusing to patch -- this file doesn't match what this script expects."
        )
    return content.replace(marker, replacement, 1)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python apply_secret_exit_patch.py <path/to/SettingActivity.smali>")
    path = sys.argv[1]

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = apply_one(content, LOCALS_MARKER, LOCALS_REPLACEMENT, "locals declaration")
    content = apply_one(content, RETURN_MARKER, RETURN_REPLACEMENT, "final return-void")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}: SecretExitTapListener wired onto view1")


if __name__ == "__main__":
    main()
