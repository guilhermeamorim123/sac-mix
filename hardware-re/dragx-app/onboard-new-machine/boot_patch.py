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


def parse_mtdparts(cmdline_text):
    """Parses the mtdparts= substring of /proc/cmdline into an ordered list
    of (name, offset_sectors, size_sectors) tuples.

    Format: mtdparts=<mtd-id>:<size>@<offset>(<name>)[,<size>@<offset>(<name>)...]
    The last partition's size may be "-" (meaning "rest of the device"),
    which is represented here as size_sectors = -1.
    """
    marker = "mtdparts="
    start = cmdline_text.find(marker)
    if start == -1:
        return []
    rest = cmdline_text[start + len(marker):]
    end = rest.find(" ")
    mtdparts = rest if end == -1 else rest[:end]
    # Strip the leading "<mtd-id>:" device prefix (e.g. "rk29xxnand:").
    if ":" in mtdparts:
        mtdparts = mtdparts.split(":", 1)[1]
    entries = []
    for part in mtdparts.split(","):
        part = part.strip()
        if not part or "@" not in part:
            continue
        size_str, remainder = part.split("@", 1)
        offset_str = remainder.split("(")[0]
        name = remainder.split("(")[1].rstrip(")")
        size_sectors = -1 if size_str == "-" else int(size_str, 16)
        entries.append((name, int(offset_str, 16), size_sectors))
    return entries


def find_partition_device(mtdparts_entries, name):
    """Given parsed mtdparts entries, returns (partition_number, size_bytes)
    for the named partition, assuming partitions are numbered 1..N in the
    order they appear in mtdparts (confirmed true for this device family by
    cross-checking against /proc/partitions block counts on the original
    machine). Returns None if not found.

    Raises ValueError if the matched entry's size_sectors is the -1 sentinel
    (see parse_mtdparts docstring) -- this means the mtdparts string used
    "-" for this partition's size ("rest of the device"), so its real byte
    size is not knowable from mtdparts alone. Callers needing this
    partition's size must obtain it some other way (e.g. device block
    count); this function will not silently return a bogus negative size.
    """
    for i, (part_name, offset_sectors, size_sectors) in enumerate(mtdparts_entries, start=1):
        if part_name == name:
            if size_sectors == -1:
                raise ValueError(
                    f"partition {name!r} has no known size in mtdparts "
                    f"(size was '-', meaning 'rest of the device'); "
                    f"cannot compute size_bytes"
                )
            return i, size_sectors * 512
    return None


def parse_boot_image(image_bytes):
    """Splits a raw boot partition dump into (compressed_ramdisk, kernel_tail).
    Raises ValueError if the KRNL magic is missing."""
    if image_bytes[:4] != KRNL_MAGIC:
        raise ValueError(f"expected KRNL magic, got {image_bytes[:4]!r}")
    size_field = struct.unpack("<I", image_bytes[4:8])[0]
    compressed_ramdisk = image_bytes[8:8 + size_field]
    kernel_tail = image_bytes[8 + size_field:]
    return compressed_ramdisk, kernel_tail


def decompress_ramdisk(compressed_ramdisk):
    """Decompresses the gzip-compressed cpio ramdisk. Uses a raw
    decompressobj (not gzip.decompress()) because in some callers this gets
    handed a compressed_ramdisk slice that was computed from a size field
    that might not be perfectly exact -- this tolerates minor trailing
    slop rather than raising on it."""
    d = zlib.decompressobj(zlib.MAX_WBITS | 16)
    ramdisk = d.decompress(compressed_ramdisk)
    return ramdisk
