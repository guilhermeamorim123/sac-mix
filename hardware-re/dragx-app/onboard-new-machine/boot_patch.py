"""
Reusable functions for parsing, patching, and verifying this device family's
Rockchip boot partition format (KRNL header + gzip-compressed cpio ramdisk +
raw kernel tail). See hardware-re/dragx-app/boot-partition-mod/README.md for
the full format writeup and history of how this was reverse-engineered and
first applied (by hand) to the original CUTTER_E326 machine.
"""
import struct
import zlib
import gzip

KRNL_MAGIC = b"KRNL"

ADB_TCP_TRIGGER = (
    b"\n"
    b"on boot\n"
    b"    setprop persist.adb.tcp.port 5555\n"
    b"    stop adbd\n"
    b"    start adbd\n"
)
