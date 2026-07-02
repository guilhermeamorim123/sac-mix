"""
Self-check for the pure-logic functions in server.py.
Run directly: python selfcheck.py
Prints PASS/FAIL for each case; exits with code 1 if anything failed.
"""
import sys

import server

failures = 0


def check(name, actual, expected):
    global failures
    if actual == expected:
        print(f"PASS: {name}")
    else:
        failures += 1
        print(f"FAIL: {name} -- expected {expected!r}, got {actual!r}")


# --- parse_connect_result ---
check(
    "connect success",
    server.parse_connect_result("connected to 192.168.15.13:5555\n"),
    True,
)
check(
    "already connected is success",
    server.parse_connect_result("already connected to 192.168.15.13:5555\n"),
    True,
)
check(
    "connect failure",
    server.parse_connect_result("unable to connect to 192.168.15.13:5555: Connection refused\n"),
    False,
)

# --- parse_install_result ---
check(
    "install success",
    server.parse_install_result("Performing Streamed Install\nSuccess\n"),
    True,
)
check(
    "install failure",
    server.parse_install_result("Performing Streamed Install\n"),
    False,
)

# --- parse_package_dir ---
check(
    "parses package dir",
    server.parse_package_dir("package:/data/app/cn.upus.app.upprinting-2/base.apk\n"),
    "/data/app/cn.upus.app.upprinting-2",
)
check(
    "empty pm path output returns None",
    server.parse_package_dir(""),
    None,
)


# --- verify_patch ---
jni_patch = server.PATCHES[0]
cert_patch = server.PATCHES[1]

check(
    "jni patch passes with patched bytes",
    server.verify_patch(jni_patch, bytes.fromhex("00bf"))[0],
    True,
)
check(
    "jni patch fails with original bytes",
    server.verify_patch(jni_patch, bytes.fromhex("04bf"))[0],
    False,
)
check(
    "cert patch passes with patched bytes",
    server.verify_patch(cert_patch, bytes.fromhex("002000bf"))[0],
    True,
)
check(
    "cert patch fails with original bytes",
    server.verify_patch(cert_patch, bytes.fromhex("f9f710ea"))[0],
    False,
)
check(
    "failure reports both expected and actual hex",
    server.verify_patch(jni_patch, bytes.fromhex("1122"))[1:],
    ("00 bf", "11 22"),
)


# --- deploy() orchestration, using a fake run_adb (monkeypatch) ---

FAKE_PACKAGE_DIR = "/data/app/cn.upus.app.upprinting-2"


def _install_fake_run_adb(fake_fn):
    """Returns the original server.run_adb so the caller can restore it."""
    original = server.run_adb
    server.run_adb = fake_fn
    return original


def _happy_path_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 0, "connected to 192.168.15.13:5555\n", ""
    if args == ["install", "-r", server.APK_PATH]:
        return 0, "Performing Streamed Install\nSuccess\n", ""
    if args == ["shell", "am", "force-stop", server.TARGET_PACKAGE]:
        return 0, "", ""
    if args == ["shell", "pm", "path", server.TARGET_PACKAGE]:
        return 0, f"package:{FAKE_PACKAGE_DIR}/base.apk\n", ""
    if len(args) == 2 and args[0] == "shell" and "skip=90350" in args[1]:
        return 0, "00 bf\n", ""
    if len(args) == 2 and args[0] == "shell" and "skip=75988" in args[1]:
        return 0, "00 20 00 bf\n", ""
    return 1, "", f"unexpected call: {args}"


original_run_adb = _install_fake_run_adb(_happy_path_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("deploy happy path overall_success", report["overall_success"], True)
check("deploy happy path step count", len(report["steps"]), 5)
check("deploy happy path all steps success", all(s["status"] == "success" for s in report["steps"]), True)


def _connect_failure_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 1, "", "unable to connect to 192.168.15.13:5555: Connection refused\n"
    return 1, "", f"should not be called: {args}"


original_run_adb = _install_fake_run_adb(_connect_failure_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("connect failure overall_success", report["overall_success"], False)
check("connect failure step count", len(report["steps"]), 1)
check("connect failure last step is failure", report["steps"][-1]["status"], "failure")


def _install_failure_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 0, "connected to 192.168.15.13:5555\n", ""
    if args == ["install", "-r", server.APK_PATH]:
        return 1, "", "adb: failed to install: INSTALL_FAILED_INSUFFICIENT_STORAGE\n"
    return 1, "", f"should not be called: {args}"


original_run_adb = _install_fake_run_adb(_install_failure_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("install failure overall_success", report["overall_success"], False)
check("install failure step count", len(report["steps"]), 2)
check("install failure last step is failure", report["steps"][-1]["status"], "failure")


def _cert_mismatch_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 0, "connected to 192.168.15.13:5555\n", ""
    if args == ["install", "-r", server.APK_PATH]:
        return 0, "Performing Streamed Install\nSuccess\n", ""
    if args == ["shell", "am", "force-stop", server.TARGET_PACKAGE]:
        return 0, "", ""
    if args == ["shell", "pm", "path", server.TARGET_PACKAGE]:
        return 0, f"package:{FAKE_PACKAGE_DIR}/base.apk\n", ""
    if len(args) == 2 and args[0] == "shell" and "skip=90350" in args[1]:
        return 0, "00 bf\n", ""
    if len(args) == 2 and args[0] == "shell" and "skip=75988" in args[1]:
        return 0, "f9 f7 10 ea\n", ""  # original, unpatched bytes
    return 1, "", f"unexpected call: {args}"


original_run_adb = _install_fake_run_adb(_cert_mismatch_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("cert mismatch overall_success", report["overall_success"], False)
check("cert mismatch last step mentions getHandshake", "getHandshake" in report["steps"][-1]["message"], True)


def _unparseable_pm_path_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 0, "connected to 192.168.15.13:5555\n", ""
    if args == ["install", "-r", server.APK_PATH]:
        return 0, "Performing Streamed Install\nSuccess\n", ""
    if args == ["shell", "am", "force-stop", server.TARGET_PACKAGE]:
        return 0, "", ""
    if args == ["shell", "pm", "path", server.TARGET_PACKAGE]:
        return 0, "", ""  # no "package:" line -- unparseable
    return 1, "", f"should not be called: {args}"


original_run_adb = _install_fake_run_adb(_unparseable_pm_path_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("unparseable pm path overall_success", report["overall_success"], False)
check("unparseable pm path step count", len(report["steps"]), 4)
check("unparseable pm path last step is failure", report["steps"][-1]["status"], "failure")


def _truncated_dd_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 0, "connected to 192.168.15.13:5555\n", ""
    if args == ["install", "-r", server.APK_PATH]:
        return 0, "Performing Streamed Install\nSuccess\n", ""
    if args == ["shell", "am", "force-stop", server.TARGET_PACKAGE]:
        return 0, "", ""
    if args == ["shell", "pm", "path", server.TARGET_PACKAGE]:
        return 0, f"package:{FAKE_PACKAGE_DIR}/base.apk\n", ""
    if len(args) == 2 and args[0] == "shell" and "skip=90350" in args[1]:
        return 0, "00\n", ""  # truncated -- expected 2 bytes, got 1
    if len(args) == 2 and args[0] == "shell" and "skip=75988" in args[1]:
        return 0, "00 20 00 bf\n", ""
    return 1, "", f"unexpected call: {args}"


original_run_adb = _install_fake_run_adb(_truncated_dd_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("truncated dd overall_success", report["overall_success"], False)
check("truncated dd step count", len(report["steps"]), 5)
check("truncated dd step 4 (index 3) mentions JNI_OnLoad", "JNI_OnLoad crash bypass" in report["steps"][3]["message"], True)
check("truncated dd step 5 (index 4) is success", report["steps"][4]["status"], "success")


def _malformed_hex_fake(args):
    if args == ["connect", "192.168.15.13:5555"]:
        return 0, "connected to 192.168.15.13:5555\n", ""
    if args == ["install", "-r", server.APK_PATH]:
        return 0, "Performing Streamed Install\nSuccess\n", ""
    if args == ["shell", "am", "force-stop", server.TARGET_PACKAGE]:
        return 0, "", ""
    if args == ["shell", "pm", "path", server.TARGET_PACKAGE]:
        return 0, f"package:{FAKE_PACKAGE_DIR}/base.apk\n", ""
    if len(args) == 2 and args[0] == "shell" and "skip=90350" in args[1]:
        return 0, "00 gg\n", ""  # right token count (2), but "gg" isn't valid hex
    if len(args) == 2 and args[0] == "shell" and "skip=75988" in args[1]:
        return 0, "00 20 00 bf\n", ""
    return 1, "", f"unexpected call: {args}"


original_run_adb = _install_fake_run_adb(_malformed_hex_fake)
report = server.deploy("192.168.15.13:5555")
server.run_adb = original_run_adb

check("malformed hex overall_success", report["overall_success"], False)
check("malformed hex step count", len(report["steps"]), 5)
check("malformed hex step 4 (index 3) is failure", report["steps"][3]["status"], "failure")
check("malformed hex step 5 (index 4) is success", report["steps"][4]["status"], "success")

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
