"""
Patches FilmCutActivity.smali (2 sites) and CustomCutActivity.smali (1 site)
to call CutReporter.reportCut() immediately after each real cut is
dispatched to the cutting hardware -- see
docs/superpowers/specs/2026-07-17-cut-balance-design.md. These are the
exact, unconditional hardware-dispatch call sites identified by research
into decoded_real_branded: they fire on every real cut regardless of the
vendor's own (already-bypassed) billing-mode setting.

Run against decoded_real_branded/ before rebuilding the APK:
    python apply_cut_reporter_patch.py
"""
import pathlib

ROOT = pathlib.Path(__file__).parent / "decoded_real_branded" / "smali" / "cn" / "upus" / "app" / "upprinting" / "dragx" / "ui" / "activity"

FILM_CUT_PATH = ROOT / "FilmCutActivity.smali"
CUSTOM_CUT_PATH = ROOT / "CustomCutActivity.smali"

CUT_REPORTER_CALL = "    invoke-static {}, Lcn/upus/app/upprinting/dragx/ui/activity/CutReporter;->reportCut()V\n"


def patch_film_cut():
    text = FILM_CUT_PATH.read_text(encoding="utf-8")

    site_1_before = (
        "    .line 38\n"
        "    invoke-virtual {v0, v1}, Lcn/upus/app/upprinting/dragx/base/BaseDataBindingActivity;->d([B)V\n"
        "\n"
        "    goto :goto_6\n"
    )
    site_1_after = (
        "    .line 38\n"
        "    invoke-virtual {v0, v1}, Lcn/upus/app/upprinting/dragx/base/BaseDataBindingActivity;->d([B)V\n"
        "\n"
        + CUT_REPORTER_CALL
        + "\n"
        "    goto :goto_6\n"
    )
    assert text.count(site_1_before) == 1, "FilmCutActivity site 1 (cond_8 branch) marker not found or not unique -- refusing to patch"
    text = text.replace(site_1_before, site_1_after, 1)

    site_2_before = (
        "    .line 40\n"
        "    invoke-virtual {v0, v1}, Lcn/upus/app/upprinting/dragx/base/BaseDataBindingActivity;->d([B)V\n"
        "\n"
        "    :goto_6\n"
        "    return-void\n"
        ".end method\n"
    )
    site_2_after = (
        "    .line 40\n"
        "    invoke-virtual {v0, v1}, Lcn/upus/app/upprinting/dragx/base/BaseDataBindingActivity;->d([B)V\n"
        "\n"
        + CUT_REPORTER_CALL
        + "\n"
        "    :goto_6\n"
        "    return-void\n"
        ".end method\n"
    )
    assert text.count(site_2_before) == 1, "FilmCutActivity site 2 (cond_9 branch) marker not found or not unique -- refusing to patch"
    text = text.replace(site_2_before, site_2_after, 1)

    FILM_CUT_PATH.write_text(text, encoding="utf-8")
    print(f"Patched {FILM_CUT_PATH} (2 sites)")


def patch_custom_cut():
    text = CUSTOM_CUT_PATH.read_text(encoding="utf-8")

    site_before = (
        "    .line 21\n"
        "    invoke-virtual {p0, v0}, Lcn/upus/app/upprinting/dragx/base/BaseDataBindingActivity;->d([B)V\n"
        "\n"
        "    .line 22\n"
        "    iget-boolean v0, p0, Lcn/upus/app/upprinting/dragx/ui/activity/CustomCutActivity;->C:Z\n"
    )
    site_after = (
        "    .line 21\n"
        "    invoke-virtual {p0, v0}, Lcn/upus/app/upprinting/dragx/base/BaseDataBindingActivity;->d([B)V\n"
        "\n"
        + CUT_REPORTER_CALL
        + "\n"
        "    .line 22\n"
        "    iget-boolean v0, p0, Lcn/upus/app/upprinting/dragx/ui/activity/CustomCutActivity;->C:Z\n"
    )
    assert text.count(site_before) == 1, "CustomCutActivity dispatch site marker not found or not unique -- refusing to patch"
    text = text.replace(site_before, site_after, 1)

    CUSTOM_CUT_PATH.write_text(text, encoding="utf-8")
    print(f"Patched {CUSTOM_CUT_PATH} (1 site)")


if __name__ == "__main__":
    patch_film_cut()
    patch_custom_cut()
