"""
Self-check for onboard.py's checkin_with_panel() -- the one part of
onboard.py that's pure enough (given a fake HTTP layer) to test without a
real device or a real network call. The three real phases
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
    return 200


onboard._post_json = fake_post_json_success
ok, message = onboard.checkin_with_panel("SERIAL123", "V7.0.3.005")
check("checkin_with_panel returns True on a 200 response", ok, True)
check("checkin_with_panel posts to the /api/machines/checkin path", captured["url"], "https://fake-panel.example.com/api/machines/checkin")
check("checkin_with_panel sends the serial in the payload", captured["payload"]["serial"], "SERIAL123")
check("checkin_with_panel sends the dragx_version in the payload", captured["payload"]["dragx_version"], "V7.0.3.005")
check("checkin_with_panel sends the API key header", captured["headers"]["X-Api-Key"], "fake-key")

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

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
