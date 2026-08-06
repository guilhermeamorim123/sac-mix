"""
Wraps both calls to NetworkUtils.setWifiEnabled(Z)V inside
DataDownloadUnzipActivity.smali in a local try/catch that swallows any
Throwable. Root cause (confirmed live via logcat, 2026-07-21): on this
hardware/OS, NetworkUtils.setWifiEnabled() throws
"SecurityException: ... was not granted this permission:
android.permission.WRITE_SETTINGS" -- WRITE_SETTINGS is a special
user-grantable permission this app was never given, and the vendor's own
synchronized-method catchall (P()'s :catchall_0) only releases the
monitor lock before RE-THROWING, so the exception was propagating all
the way up and killing the whole app process mid-download.

Neither call's result is used for anything downstream -- disabling/
re-enabling WiFi during a data download is a best-effort optimization,
not something the rest of the method depends on -- so silently
swallowing a failure here is safe and matches this project's general
principle of not touching behavior beyond the specific crash.

Run once against decoded_newpkg's DataDownloadUnzipActivity.smali:
    python apply_wifi_crash_fix_patch.py \
        decoded_newpkg/smali/cn/upus/app/upprinting/dragx/ui/activity/setting/DataDownloadUnzipActivity.smali
"""
import sys

SITE_1_MARKER = (
    "    const/4 v2, 0x1\n"
    "\n"
    "    .line 130\n"
    "    invoke-static {v2}, Lcom/blankj/utilcode/util/NetworkUtils;->setWifiEnabled(Z)V\n"
    "\n"
    "    .line 131\n"
    "    invoke-virtual/range {p0 .. p0}, Landroid/app/Activity;->finish()V\n"
)

SITE_1_REPLACEMENT = (
    "    const/4 v2, 0x1\n"
    "\n"
    "    .line 130\n"
    "    :try_start_wifireset1\n"
    "    invoke-static {v2}, Lcom/blankj/utilcode/util/NetworkUtils;->setWifiEnabled(Z)V\n"
    "\n"
    "    goto :wifireset1_ok\n"
    "\n"
    "    :catch_wifireset1\n"
    "    move-exception v2\n"
    "\n"
    "    :wifireset1_ok\n"
    "    :try_end_wifireset1\n"
    "    .catch Ljava/lang/Throwable; {:try_start_wifireset1 .. :try_end_wifireset1} :catch_wifireset1\n"
    "\n"
    "    .line 131\n"
    "    invoke-virtual/range {p0 .. p0}, Landroid/app/Activity;->finish()V\n"
)

SITE_2_MARKER = (
    "    const/4 v0, 0x0\n"
    "\n"
    "    .line 4\n"
    "    invoke-static {v0}, Lcom/blankj/utilcode/util/NetworkUtils;->setWifiEnabled(Z)V\n"
    "\n"
    "    .line 5\n"
    "    new-instance v0, Ljava/lang/Thread;\n"
)

SITE_2_REPLACEMENT = (
    "    const/4 v0, 0x0\n"
    "\n"
    "    .line 4\n"
    "    :try_start_wifireset2\n"
    "    invoke-static {v0}, Lcom/blankj/utilcode/util/NetworkUtils;->setWifiEnabled(Z)V\n"
    "\n"
    "    goto :wifireset2_ok\n"
    "\n"
    "    :catch_wifireset2\n"
    "    move-exception v0\n"
    "\n"
    "    :wifireset2_ok\n"
    "    :try_end_wifireset2\n"
    "    .catch Ljava/lang/Throwable; {:try_start_wifireset2 .. :try_end_wifireset2} :catch_wifireset2\n"
    "\n"
    "    .line 5\n"
    "    new-instance v0, Ljava/lang/Thread;\n"
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
        raise SystemExit("usage: python apply_wifi_crash_fix_patch.py <path/to/DataDownloadUnzipActivity.smali>")
    path = sys.argv[1]

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = apply_one(content, SITE_1_MARKER, SITE_1_REPLACEMENT, "site 1 (re-enable WiFi)")
    content = apply_one(content, SITE_2_MARKER, SITE_2_REPLACEMENT, "site 2 (disable WiFi, inside P())")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}: both setWifiEnabled() calls now wrapped in a swallowing try/catch")


if __name__ == "__main__":
    main()
