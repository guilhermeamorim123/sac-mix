"""
Self-check for boot_patch.py, tested against the real boot partition dumps
already captured and verified working (via a real power-cycle test) on the
original CUTTER_E326 machine. See
hardware-re/dragx-app/boot-partition-mod/README.md for how these fixtures
were produced.

Run directly: python boot_patch_selfcheck.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boot_patch  # noqa: E402

failures = 0


def check(name, actual, expected):
    global failures
    if actual == expected:
        print(f"PASS: {name}")
    else:
        failures += 1
        print(f"FAIL: {name} -- expected {expected!r}, got {actual!r}")


def check_true(name, actual):
    check(name, bool(actual), True)


FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "boot-partition-mod"
)
ORIGINAL_PATH = os.path.join(FIXTURE_DIR, "boot_partition_ORIGINAL_backup.img")
MODIFIED_PATH = os.path.join(FIXTURE_DIR, "boot_partition_MODIFIED_wifi-adb-persistent.img")

if not os.path.exists(ORIGINAL_PATH):
    print(f"FIXTURE MISSING: {ORIGINAL_PATH}")
    sys.exit(1)

original_bytes = open(ORIGINAL_PATH, "rb").read()

# --- parse_mtdparts ---
sample_cmdline = (
    "vmalloc=496M rockchip_jtag console=ttyFIQ0 androidboot.baseband=N/A "
    "mtdparts=rk29xxnand:0x00002000@0x00002000(uboot),0x00002000@0x00004000(trust),"
    "0x00002000@0x00006000(misc),0x00008000@0x00008000(resource),"
    "0x00006000@0x00010000(kernel),0x00006000@0x00016000(boot),"
    "0x00010000@0x0001C000(recovery),0x00020000@0x0002C000(backup),"
    "0x00040000@0x0004C000(cache),0x00008000@0x0008C000(metadata),"
    "0x00002000@0x00094000(kpanic),0x00400000@0x00096000(system),"
    "0x00020000@0x00496000(radical_update),-@0x004B6000(userdata) "
    "storagemedia=emmc"
)
entries = boot_patch.parse_mtdparts(sample_cmdline)
check("parse_mtdparts entry count", len(entries), 14)
check("parse_mtdparts 6th entry is boot", entries[5][0], "boot")

result = boot_patch.find_partition_device(entries, "boot")
check("find_partition_device boot number", result[0], 6)
check("find_partition_device boot size bytes", result[1], 12582912)

try:
    boot_patch.find_partition_device(entries, "userdata")
    raised = False
except ValueError:
    raised = True
check_true("find_partition_device raises ValueError for unresolvable ('-') size", raised)

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
