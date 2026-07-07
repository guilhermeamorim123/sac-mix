"""
Self-check for the parts of onboard.py that are pure enough (given a fake
HTTP layer / a monkeypatched run_adb) to test without a real device or a
real network call: checkin_with_panel(), _parse_version_name(), and the
ADB command arguments built by get_device_serial(). The three real phases
(phase1/phase2/phase3) are validated by real hardware runs instead, per
docs/superpowers/plans/2026-07-02-onboard-new-machine.md's own approach.

Run directly: python onboard_selfcheck.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import onboard  # noqa: E402

failures = 0


def check(name, actual, expected):
    global failures
    if actual == expected:
        print(f"PASS: {name}")
    else:
        failures += 1
        print(f"FAIL: {name} -- expected {expected!r}, got {actual!r}")


# --- checkin_with_panel: missing config ---
os.environ.pop("PANEL_URL", None)
os.environ.pop("PANEL_API_KEY", None)
ok, message = onboard.checkin_with_panel("SERIAL123", "V7.0.3.005")
check("checkin_with_panel returns False when PANEL_URL/PANEL_API_KEY are unset", ok, False)

# --- checkin_with_panel: success (fake HTTP layer) ---
os.environ["PANEL_URL"] = "https://fake-panel.example.com"
os.environ["PANEL_API_KEY"] = "fake-key"

captured = {}


def fake_post_json_success(url, payload_dict, headers, timeout=10):
    captured["url"] = url
    captured["payload"] = payload_dict
    captured["headers"] = headers
    captured["timeout"] = timeout
    return 200


onboard._post_json = fake_post_json_success
ok, message = onboard.checkin_with_panel("SERIAL123", "V7.0.3.005")
check("checkin_with_panel returns True on a 200 response", ok, True)
check("checkin_with_panel posts to the /api/machines/checkin path", captured["url"], "https://fake-panel.example.com/api/machines/checkin")
check("checkin_with_panel sends the serial in the payload", captured["payload"]["serial"], "SERIAL123")
check("checkin_with_panel sends the dragx_version in the payload", captured["payload"]["dragx_version"], "V7.0.3.005")
check("checkin_with_panel sends the API key header", captured["headers"]["X-Api-Key"], "fake-key")
# Regression test: checkin_with_panel must pass a cold-start-tolerant
# timeout (60s), not _post_json's own 10s default -- Render's free tier
# can take 30-50s to wake from sleep, and onboard.py runs are infrequent
# enough that the panel will very plausibly be asleep on a real run.
check("checkin_with_panel passes a 60s timeout to _post_json (tolerates a Render free-tier cold start)", captured["timeout"], 60)

# --- checkin_with_panel: non-200 response ---
def fake_post_json_failure(url, payload_dict, headers, timeout=10):
    return 500


onboard._post_json = fake_post_json_failure
ok, message = onboard.checkin_with_panel("SERIAL123", "V7.0.3.005")
check("checkin_with_panel returns False on a non-200 response", ok, False)

# --- checkin_with_panel: network error ---
def fake_post_json_raises(url, payload_dict, headers, timeout=10):
    raise ConnectionError("connection refused")


onboard._post_json = fake_post_json_raises
ok, message = onboard.checkin_with_panel("SERIAL123", "V7.0.3.005")
check("checkin_with_panel returns False (not raises) on a network error", ok, False)

# --- _parse_version_name: realistic multi-line dumpsys output ---
dumpsys_output = """
Packages:
  Package [com.dragx.app] (abcdef):
    userId=10123
    pkg=Package{1234567 com.dragx.app}
    versionCode=705 minSdk=21 targetSdk=29
    versionName=V7.0.3.005
    splits=[base]
    apkSigningVersion=2
"""
check(
    "_parse_version_name finds versionName= among other dumpsys lines",
    onboard._parse_version_name(dumpsys_output),
    "V7.0.3.005",
)

# --- _parse_version_name: no versionName= line at all ---
check(
    "_parse_version_name returns None when there's no versionName= line",
    onboard._parse_version_name("Packages:\n  Package [com.dragx.app] (abcdef):\n    userId=10123\n"),
    None,
)

# --- _parse_version_name: first match wins (documented, intentional behavior) ---
two_versions_output = """
    versionName=V7.0.3.005
    versionName=V9.9.9.999
"""
check(
    "_parse_version_name returns the FIRST versionName= match when multiple are present",
    onboard._parse_version_name(two_versions_output),
    "V7.0.3.005",
)

# --- get_device_serial: uses `getprop ro.serialno`, NOT `get-serialno` ---
# Regression test for a confirmed real-device bug: for a TCP/IP-connected
# device, `adb get-serialno` returns the ip:port transport address itself
# (e.g. "192.168.15.13:5555"), not the hardware serial -- confirmed against
# a real device, where `adb -s <ip>:5555 shell getprop ro.serialno`
# correctly returned "6S9OZFRLDN" while `adb -s <ip>:5555 get-serialno`
# incorrectly returned the ip:port string back. There's no parsing logic to
# unit-test in isolation here (the whole function is "run one ADB command,
# strip the output"), so this just locks in the command arguments via a
# monkeypatched run_adb, the same pattern used for _post_json above.
captured_adb_args = {}


def fake_run_adb_for_serial(args):
    captured_adb_args["args"] = args
    return 0, "6S9OZFRLDN\n", ""


real_run_adb = onboard.run_adb
onboard.run_adb = fake_run_adb_for_serial
serial = onboard.get_device_serial("192.168.15.13:5555")
onboard.run_adb = real_run_adb
check(
    "get_device_serial calls `shell getprop ro.serialno`, not `get-serialno`",
    captured_adb_args["args"],
    ["-s", "192.168.15.13:5555", "shell", "getprop", "ro.serialno"],
)
check("get_device_serial returns the stripped hardware serial", serial, "6S9OZFRLDN")

# --- get_usb_serial: picks the bare-serial USB entry, ignores ip:port entries ---
def fake_run_adb_usb_only(args):
    return 0, "List of devices attached\n6S9OZFRLDN\tdevice\n\n", ""


onboard.run_adb = fake_run_adb_usb_only
check("get_usb_serial finds a lone USB-connected device", onboard.get_usb_serial(), "6S9OZFRLDN")


def fake_run_adb_usb_and_wifi(args):
    return 0, "List of devices attached\n6S9OZFRLDN\tdevice\n192.168.15.6:5555\tdevice\n\n", ""


onboard.run_adb = fake_run_adb_usb_and_wifi
check(
    "get_usb_serial ignores ip:port entries even when a WiFi device is also listed",
    onboard.get_usb_serial(),
    "6S9OZFRLDN",
)


def fake_run_adb_no_devices(args):
    return 0, "List of devices attached\n\n", ""


onboard.run_adb = fake_run_adb_no_devices
check("get_usb_serial returns None when no device is connected", onboard.get_usb_serial(), None)


def fake_run_adb_unauthorized(args):
    return 0, "List of devices attached\n6S9OZFRLDN\tunauthorized\n\n", ""


onboard.run_adb = fake_run_adb_unauthorized
check("get_usb_serial ignores a non-'device' status (e.g. unauthorized)", onboard.get_usb_serial(), None)

onboard.run_adb = real_run_adb

# --- _install_failure_is_version_conflict: detects the two known conflict signatures ---
version_downgrade_report = {
    "overall_success": False,
    "steps": [
        {"status": "success", "message": "Conectado a 192.168.15.6:5555"},
        {"status": "failure", "message": "Falha ao instalar: Failure [INSTALL_FAILED_VERSION_DOWNGRADE]"},
    ],
}
check(
    "_install_failure_is_version_conflict detects INSTALL_FAILED_VERSION_DOWNGRADE",
    onboard._install_failure_is_version_conflict(version_downgrade_report),
    True,
)

update_incompatible_report = {
    "overall_success": False,
    "steps": [
        {"status": "failure", "message": "Falha ao instalar: Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]"},
    ],
}
check(
    "_install_failure_is_version_conflict detects INSTALL_FAILED_UPDATE_INCOMPATIBLE",
    onboard._install_failure_is_version_conflict(update_incompatible_report),
    True,
)

unrelated_failure_report = {
    "overall_success": False,
    "steps": [
        {"status": "failure", "message": "Não foi possível conectar em 192.168.15.6:5555: timeout"},
    ],
}
check(
    "_install_failure_is_version_conflict returns False for an unrelated failure",
    onboard._install_failure_is_version_conflict(unrelated_failure_report),
    False,
)

success_report = {
    "overall_success": True,
    "steps": [{"status": "success", "message": "DragX instalado"}],
}
check(
    "_install_failure_is_version_conflict returns False when there's no failure at all",
    onboard._install_failure_is_version_conflict(success_report),
    False,
)

# --- recover_from_version_conflict: refuses to proceed without a USB cable ---
ok, message = onboard.recover_from_version_conflict(None, "192.168.15.6:5555")
check("recover_from_version_conflict refuses to run without usb_serial", ok, False)
check(
    "recover_from_version_conflict's message mentions the USB cable when refusing",
    "USB" in message,
    True,
)

# --- _wait_until_responsive: returns True as soon as a shell echo succeeds ---
def fake_run_adb_responsive(args):
    if args[:1] == ["connect"]:
        return 0, "connected to 192.168.15.19:5555\n", ""
    return 0, "ok\n", ""


onboard.run_adb = fake_run_adb_responsive
check(
    "_wait_until_responsive returns True as soon as the device answers",
    onboard._wait_until_responsive("192.168.15.19:5555", timeout_seconds=5, poll_interval=1),
    True,
)


def fake_run_adb_never_responsive(args):
    if args[:1] == ["connect"]:
        return 1, "", "unable to connect\n"
    return 1, "", "device offline\n"


onboard.run_adb = fake_run_adb_never_responsive
check(
    "_wait_until_responsive returns False after timing out",
    onboard._wait_until_responsive("192.168.15.19:5555", timeout_seconds=2, poll_interval=1),
    False,
)

onboard.run_adb = real_run_adb

# --- wait_for_boot: returns True as soon as sys.boot_completed reads "1" ---
def fake_run_adb_boot_completed(args):
    return 0, "1\n", ""


onboard.run_adb = fake_run_adb_boot_completed
check(
    "wait_for_boot returns True immediately when sys.boot_completed is already 1",
    onboard.wait_for_boot("6S9OZFRLDN", timeout_seconds=5, poll_interval=1),
    True,
)


def fake_run_adb_never_boots(args):
    return 0, "\n", ""


onboard.run_adb = fake_run_adb_never_boots
check(
    "wait_for_boot returns False after timing out",
    onboard.wait_for_boot("6S9OZFRLDN", timeout_seconds=2, poll_interval=1),
    False,
)

onboard.run_adb = real_run_adb

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
