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


# --- parse_boot_image (against the real original-machine fixture) ---
compressed_ramdisk, kernel_tail = boot_patch.parse_boot_image(original_bytes)
check("parse_boot_image kernel_tail length", len(kernel_tail), 11108616)
check("parse_boot_image compressed_ramdisk starts with gzip magic", compressed_ramdisk[:2], b"\x1f\x8b")

# --- decompress_ramdisk ---
ramdisk = boot_patch.decompress_ramdisk(compressed_ramdisk)
check("decompress_ramdisk length", len(ramdisk), 2868736)
check("decompress_ramdisk starts with cpio magic", ramdisk[:6], b"070701")


# --- parse_cpio_entries ---
cpio_entries = boot_patch.parse_cpio_entries(ramdisk)
check("parse_cpio_entries count", len(cpio_entries), 57)
check("parse_cpio_entries last is TRAILER", cpio_entries[-1]["name"], "TRAILER!!!")

init_usb_rc = boot_patch.find_entry(cpio_entries, "init.usb.rc")
check_true("find_entry locates init.usb.rc", init_usb_rc is not None)
check("original init.usb.rc size", init_usb_rc["filesize"], 5715)
check_true(
    "original init.usb.rc has no trigger yet",
    boot_patch.ADB_TCP_TRIGGER not in init_usb_rc["filedata"],
)
check_true("find_entry returns None for missing name", boot_patch.find_entry(cpio_entries, "nonexistent.rc") is None)

# --- parse_cpio_entries rejects a corrupted header with a negative namesize
# instead of risking an infinite loop (see boot_patch.py docstring: a literal
# '-' in a hex field parses fine via int(s, 16) but breaks the offset-always-
# advances invariant) ---
_malformed_header = (
    b"070701"       # magic
    + b"00000000"   # c_ino
    + b"00000000"   # c_mode
    + b"00000000"   # c_uid
    + b"00000000"   # c_gid
    + b"00000000"   # c_nlink
    + b"00000000"   # c_mtime
    + b"00000000"   # c_filesize
    + b"00000000"   # c_devmajor
    + b"00000000"   # c_devminor
    + b"00000000"   # c_rdevmajor
    + b"00000000"   # c_rdevminor
    + b"-0000001"   # c_namesize -- decodes to -1 via int("-0000001", 16)
    + b"00000000"   # c_check
)
assert len(_malformed_header) == 110, f"malformed test header is {len(_malformed_header)} bytes, expected 110"
try:
    boot_patch.parse_cpio_entries(_malformed_header)
    malformed_raised = False
except ValueError:
    malformed_raised = True
check_true("parse_cpio_entries raises ValueError promptly on negative namesize (no hang)", malformed_raised)

# --- patch_init_usb_rc (fresh, unpatched entries) ---
patched_entries, already_patched = boot_patch.patch_init_usb_rc(list(cpio_entries))
check("patch_init_usb_rc already_patched (fresh)", already_patched, False)
patched_init_usb_rc = boot_patch.find_entry(patched_entries, "init.usb.rc")
check(
    "patched init.usb.rc size",
    patched_init_usb_rc["filesize"],
    5715 + len(boot_patch.ADB_TCP_TRIGGER),
)
check_true(
    "patched init.usb.rc contains trigger",
    boot_patch.ADB_TCP_TRIGGER in patched_init_usb_rc["filedata"],
)

# --- idempotency: patching already-patched entries is a safe no-op ---
patched_again, already_patched_2 = boot_patch.patch_init_usb_rc(list(patched_entries))
check("patch_init_usb_rc already_patched (second time)", already_patched_2, True)
patched_again_init_usb_rc = boot_patch.find_entry(patched_again, "init.usb.rc")
check(
    "second patch does not duplicate the trigger",
    patched_again_init_usb_rc["filesize"],
    5715 + len(boot_patch.ADB_TCP_TRIGGER),
)


# --- rebuild_cpio + full round trip against the fresh patch ---
new_ramdisk = boot_patch.rebuild_cpio(patched_entries)
reparsed = boot_patch.parse_cpio_entries(new_ramdisk)
check("rebuilt cpio entry count", len(reparsed), 57)
check("rebuilt cpio last entry is TRAILER", reparsed[-1]["name"], "TRAILER!!!")
reparsed_init = boot_patch.find_entry(reparsed, "init.usb.rc")
check_true("rebuilt init.usb.rc contains trigger", boot_patch.ADB_TCP_TRIGGER in reparsed_init["filedata"])

# --- compress_ramdisk_to_fit ---
compressed = boot_patch.compress_ramdisk_to_fit(new_ramdisk, max_compressed_size=1474288 + 10000)
check_true("compress_ramdisk_to_fit produces valid gzip", compressed[:2] == b"\x1f\x8b")
check_true("compress_ramdisk_to_fit result fits the budget", len(compressed) <= 1474288 + 10000)

# compress_ramdisk_to_fit should raise if nothing fits, even at max compression
try:
    boot_patch.compress_ramdisk_to_fit(new_ramdisk, max_compressed_size=100)
    check("compress_ramdisk_to_fit raises when nothing fits", "no exception", "ValueError")
except ValueError:
    check("compress_ramdisk_to_fit raises when nothing fits", "ValueError", "ValueError")

# --- reassemble_boot_image ---
new_image = boot_patch.reassemble_boot_image(compressed, kernel_tail, partition_size=12582912)
check("reassembled image size", len(new_image), 12582912)
check("reassembled image starts with KRNL", new_image[:4], b"KRNL")

# reassemble_boot_image should raise if the pieces don't fit
try:
    boot_patch.reassemble_boot_image(compressed, kernel_tail, partition_size=100)
    check("reassemble_boot_image raises when oversized", "no exception", "ValueError")
except ValueError:
    check("reassemble_boot_image raises when oversized", "ValueError", "ValueError")


# --- verify_roundtrip on a freshly-patched image (built in this test run) ---
ok, message = boot_patch.verify_roundtrip(new_image, expected_kernel_tail=kernel_tail, must_contain_trigger=True)
check_true(f"verify_roundtrip accepts freshly-patched image: {message}", ok)

# --- verify_roundtrip against today's REAL modified image (already reboot-tested on hardware) ---
modified_bytes = open(MODIFIED_PATH, "rb").read()
_, real_kernel_tail = boot_patch.parse_boot_image(original_bytes)
ok2, message2 = boot_patch.verify_roundtrip(modified_bytes, expected_kernel_tail=real_kernel_tail, must_contain_trigger=True)
check_true(f"verify_roundtrip accepts today's real modified image: {message2}", ok2)

# --- verify_roundtrip correctly REJECTS an unpatched image when a trigger is required ---
ok3, message3 = boot_patch.verify_roundtrip(original_bytes, expected_kernel_tail=real_kernel_tail, must_contain_trigger=True)
check("verify_roundtrip rejects unpatched original image", ok3, False)

# --- verify_roundtrip correctly rejects a kernel-tail mismatch ---
wrong_kernel_tail = b"\x00" * len(real_kernel_tail)
ok4, message4 = boot_patch.verify_roundtrip(modified_bytes, expected_kernel_tail=wrong_kernel_tail, must_contain_trigger=True)
check("verify_roundtrip rejects kernel tail mismatch", ok4, False)

# --- verify_roundtrip correctly rejects garbage input without raising ---
ok5, message5 = boot_patch.verify_roundtrip(b"not a real boot image", expected_kernel_tail=real_kernel_tail, must_contain_trigger=True)
check("verify_roundtrip rejects garbage input", ok5, False)

# --- verify_roundtrip correctly rejects a short-but-magic-matching image
# without raising (regression test: parse_boot_image raises struct.error,
# not ValueError, when the KRNL magic matches but the buffer is too short
# for the size field at bytes [4:8]) ---
ok6, message6 = boot_patch.verify_roundtrip(b"KRNL" + b"\x01\x02", expected_kernel_tail=b"", must_contain_trigger=False)
check("verify_roundtrip rejects short magic-matching input without raising", ok6, False)

if failures:
    print(f"\n{failures} check(s) FAILED")
    sys.exit(1)
else:
    print("\nAll checks passed")
