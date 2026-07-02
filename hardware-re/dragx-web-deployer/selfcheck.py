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

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
