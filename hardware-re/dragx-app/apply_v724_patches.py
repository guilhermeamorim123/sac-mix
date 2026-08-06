"""
Applies the two native patches to the v724 libnewcutjni.so, re-derived via
Ghidra headless analysis in this session (image base 0x10000 for this build,
NOT 0x100000 like the v705 build documented in NATIVE_PATCH.md -- verified
directly against file bytes before writing anything, same discipline as the
original process).

Patch A -- crypto-correctness (equivalent of old file offset 0x128d4):
  File offset 0x17466, bytes 08bf ("it eq") -> 00bf (NOP).
  This is the SECOND of two strcmp() certificate checks inside
  FUN_000267a4 (this build checks against two possible hardcoded cert
  hashes, not just one like v705). Neutralizing the "it eq" here makes the
  following `mov.eq r0,r5` execute unconditionally, forcing r0 to the
  success-state value regardless of the real strcmp result. Since the first
  strcmp's failure is what routes control into this second check in the
  first place, forcing this one to always succeed guarantees the overall
  check always passes on both possible paths (first check real-succeeds ->
  unaffected; first check fails -> falls through to this now-always-succeeds
  second check).

Patch B -- JNI_OnLoad crash bypass (equivalent of old file offset 0x160ee):
  File offset 0x1b414, bytes 0138 ("subs r0,#1") -> 0020 ("movs r0,#0").
  Unlike the v705 build (where the guarded instructions ran on the SUCCESS
  path and NOPing the IT made them unconditional-success), this build's
  polarity is reversed: the itt-guarded instructions here set the FAILURE
  state. NOPing that IT would make failure unconditional -- the wrong
  direction. Instead this patches the preceding comparison setup itself so
  the stored flag is always 0 (success), which also zeroes the Z flag,
  permanently disabling the downstream "it ne" from ever firing.
"""
import sys

SO_PATH = "decoded_v724/lib/armeabi-v7a/libnewcutjni.so"

PATCHES = [
    (0x17466, bytes.fromhex("08bf"), bytes.fromhex("00bf"), "Patch A: strcmp#2 it-eq -> NOP"),
    (0x1b414, bytes.fromhex("0138"), bytes.fromhex("0020"), "Patch B: subs r0,#1 -> movs r0,#0"),
]


def main():
    with open(SO_PATH, "rb") as f:
        data = bytearray(f.read())

    for offset, expected, new_bytes, label in PATCHES:
        actual = bytes(data[offset:offset + len(expected)])
        if actual != expected:
            print(f"ERRO: {label} -- esperava {expected.hex()} em 0x{offset:x}, achei {actual.hex()}. Abortando, nada foi escrito.")
            sys.exit(1)
        data[offset:offset + len(new_bytes)] = new_bytes
        print(f"OK: {label} aplicado em 0x{offset:x} ({expected.hex()} -> {new_bytes.hex()})")

    with open(SO_PATH, "wb") as f:
        f.write(data)
    print(f"\nGravado: {SO_PATH}")


if __name__ == "__main__":
    main()
