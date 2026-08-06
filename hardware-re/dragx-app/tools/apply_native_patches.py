"""
Applies both libnewcutjni.so binary patches documented in NATIVE_PATCH.md.

Usage:
    python apply_native_patches.py path\to\libnewcutjni.so

Both patches assert the expected original bytes before writing -- if either
assertion fails, this .so is a different build than the one these patches
were derived from (Upprinting_V7.0.3.005.apk), and the offsets must be
re-verified in Ghidra before patching (see NATIVE_PATCH.md, "Deploying to
other machines" in README.md).
"""
import sys

PATCHES = [
    {
        "name": "JNI_OnLoad exit(0) bypass",
        "offset": 0x160ee,
        "expected": bytes.fromhex("04bf"),
        "replacement": bytes.fromhex("00bf"),
    },
    {
        "name": "getHandshake() certificate-check bypass",
        "offset": 0x128d4,
        "expected": bytes.fromhex("f9f710ea"),
        "replacement": bytes.fromhex("002000bf"),
    },
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    data = bytearray(open(path, "rb").read())

    for p in PATCHES:
        off = p["offset"]
        exp = p["expected"]
        got = bytes(data[off:off + len(exp)])
        if got != exp:
            print(f"ABORT: {p['name']} -- expected {exp.hex()} at offset {hex(off)}, found {got.hex()}.")
            print("This .so does not match the build these patches were derived from.")
            print("Re-verify offsets in Ghidra before patching (see NATIVE_PATCH.md).")
            sys.exit(2)
        data[off:off + len(p["replacement"])] = p["replacement"]
        print(f"OK: {p['name']} -- patched offset {hex(off)}: {exp.hex()} -> {p['replacement'].hex()}")

    open(path, "wb").write(data)
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
