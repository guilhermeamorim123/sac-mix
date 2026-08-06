# Native anti-tamper bypass in libnewcutjni.so

## The problem

After rebranding + resigning the Upprinting APK as DragX (same package name,
self-signed key — see `README.md`), any code path that first touches
`com.cut.cutjni.JniUtils` (which triggers `System.loadLibrary("newcutjni")`
→ `JNI_OnLoad`) caused the **entire process to call `exit(0)`** — not a
Java exception, not a crash with a catchable stack trace, a deliberate
native `exit()`. Confirmed via `logcat`:

```
I qaz     : class have find
W crashsdk: libcrashsdk.so is unloading in pid: NNNN tid: NNNN. called exit?
E DEBUG   : Exiting in pid: NNNN, tid: NNNN
...
#04 pc 00051897  /system/lib/libc.so (__cxa_finalize+126)
#05 pc 000162fb  /system/lib/libc.so (exit+10)
#06 pc 0001637f  libnewcutjni.so (JNI_OnLoad+938)
```

Ruled out before finding the real cause (each confirmed independently on
the physical device, not guessed):
- **Not** about running in a fake environment — reproduced in a fully
  legitimate, Zygote-launched Activity process (not just the earlier
  `app_process` hack from the handshake-bridge work).
- **Not** about system-app status — reproduced identically after
  reinstalling DragX as a real `/system/app` entry with `flags=[ SYSTEM ... ]`
  confirmed via `dumpsys package`, native libs correctly extracted to
  `/system/app/Upprinting/lib/arm/`.
- **Not** about a missing `Context`/`Application` (that was a *different*,
  earlier problem hit and solved during the handshake-bridge work — see
  `plans/README.md` — via `ActivityThread.systemMain()`). This crash happens
  even with a completely genuine Activity lifecycle.

The remaining explanation, consistent with everything observed: **the
native library checks something that differs between the vendor's original
signed APK and our resigned one** (almost certainly APK/certificate
verification — this is standard anti-tamper practice, and we have no way to
replicate the vendor's private signing key to test that theory directly —
but it doesn't matter *what* it checks, see below).

## Root-causing with Ghidra (headless)

No GUI interaction is available in this environment, so **Ghidra's headless
analyzer** (`support/analyzeHeadless(.bat)`) was used with custom Java
scripts (`-postScript`) to decompile and disassemble
`libnewcutjni.so` (the `armeabi-v7a` copy — this device is 32-bit ARM) and
print results as text.

- **Ghidra 12.1.2** requires **JDK 21+** — this machine only had JDK 17
  (used for the DragX apktool/dex toolchain). Downloaded Temurin JDK 21
  separately; set `JAVA_HOME` to it only for Ghidra invocations.
- **Extract to a short path.** The default scratch/temp path used in this
  session was long enough that Ghidra's own zip (containing very long
  internal paths like
  `docs/ghidra_stubs/pypredef/ghidra.app.plugin.exceptionhandlers.gcc...pypredef`)
  blew past Windows' `MAX_PATH`, breaking extraction. Extracted to
  `C:\ghidra_tmp\` instead.
- **Ghidra's decompiled/disassembly addresses are not raw file offsets.**
  Ghidra applied a default image base of `0x00100000` to this ELF (it has
  `p_vaddr=0` for its first `LOAD` segment, which Ghidra's ELF loader
  rebases away from 0). A byte found via disassembly at Ghidra address
  `0x000260ee` was actually at **file offset `0x160ee`** (i.e.
  `file_offset = ghidra_address - 0x100000` for this binary). Confirmed by
  searching for the surrounding unique byte sequence directly in the raw
  file rather than trusting the naive subtraction blindly — do this
  cross-check before patching, don't assume the base offset without
  verifying against the actual file bytes.
- Scripts used: `C:\ghidra_scripts\DecompileJniOnLoad.java` (prints
  decompiled pseudo-C for `JNI_OnLoad`, plus all callers of `exit()`) and
  `DumpAsm.java` (prints raw disassembly with addresses + instruction bytes
  for a given function). Both are plain `GhidraScript` subclasses, run via:
  ```
  analyzeHeadless.bat <projectDir> <projectName> -import <path-to-so> \
    -postScript <ScriptName.java> -scriptPath <dir-containing-script>
  ```
  (drop `-import` and use `-process "<file>.so"` to rerun a script against
  an already-analyzed project without re-importing.)

## What JNI_OnLoad actually does

Decompiled, `JNI_OnLoad` is a control-flow-flattened state machine (typical
obfuscation — a `while` loop dispatching on an opaque integer "state"
variable rather than straight-line code). Traced by hand into this logical
flow:

```
GetEnv(vm, &env, JNI_VERSION_1_6)
if GetEnv failed:
    return                                    // no crash, just no RegisterNatives
else:
    r = FUN_00025e30(env)                      // presumed: primary FindClass/RegisterNatives setup
    if r == 0:
        return                                 // success path A, no crash
    else:
        r2 = FUN_0002232c(env)                 // THE CHECK
        if r2 == 1:
            __android_log_print(INFO, "qaz", "class have find")
            return                              // success path B, no crash
        else:
            exit(0)                             // <-- our crash
```

`FUN_0002232c(env)` is the deciding check. Its actual purpose was **not**
investigated further (didn't need to be — see the patch below), but given
everything ruled out above, it's most likely a signature/integrity check
against the vendor's own certificate.

## The patch

Rather than reverse-engineer what `FUN_0002232c` checks, the fix forces its
result to always be treated as `1` (success), at the one place the check
result is consumed. Disassembly around the check (`armeabi-v7a`, Ghidra
address shown, subtract `0x100000` for file offset):

```
000260d0  ldr r0,[sp,#0x4]
000260d2  bl  0x0002232c          ; r0 = FUN_0002232c(env)
000260d6  movw r6,#0x3697
000260da  cmp r0,#0x1             ; sets Z flag iff r0==1
000260dc  movw r0,#0xe11e         ; r0 = default/"failure" state (low half)
000260e0  movt r6,#0x5a6c
000260e4  movt r0,#0x1d5a         ; r0 = default/"failure" state (high half) = 0x1d5ae11e
000260e8  mvn lr,#0x1
000260ec  mov r12,r6
000260ee  itt eq                  ; <<< PATCHED: 04 bf -> 00 bf (NOP)
000260f0  movw.eq r0,#0x2967      ; only ran if Z==1 (r0 was 1) -- now always runs
000260f4  movt.eq r0,#0xdf2d      ; r0 = success state = 0xdf2d2967 (-0x20d2d699)
000260f8  b   0x00026052          ; back to state-machine dispatch
```

The 2-byte Thumb `itt eq` instruction (`04 bf`) at **file offset `0x160ee`**
was changed to a Thumb NOP (`00 bf`). An `IT` block's condition is what
makes the following instructions conditional in Thumb-2 — removing the `IT`
instruction itself makes the two `movw`/`movt` that follow execute
**unconditionally**, so `r0` always becomes the success-state value
regardless of what `FUN_0002232c` actually returned. This is a single,
minimal, self-contained patch: it doesn't touch the call to
`FUN_0002232c` itself (so any real side effects it has, e.g. actually
registering the native methods, still happen), it only neutralizes the
pass/fail branch that gates on its return value.

Applied via a small Python script that reads the `.so`, asserts the
expected original bytes at that offset (fail loudly if they don't match —
protects against silently patching the wrong location if this is ever redone
against a different vendor build), writes `04bf → 00bf`, and saves. The
patched file replaces `lib/armeabi-v7a/libnewcutjni.so` in the apktool
project (`decoded/lib/armeabi-v7a/libnewcutjni.so`) before rebuilding.

**Verified working**: after this patch, rebuild, resign, reinstall — the
same actions that previously triggered `exit(0)` (opening Settings → System
Info → "Detecção de rede", which calls `JniUtils.encryptSign()`) now
complete without crashing, logcat shows `class have find` with no
`exit`/crash lines following, and the app continues running normally.

## Second, unrelated blocker found afterward: "device disabled" gate

Once the native crash was fixed, tapping a product category (e.g.
"Smartphones") on the main screen still showed a toast: **"O dispositivo
está desativado, entre em contato com o servidor de suporte técnico"** and
didn't navigate anywhere. This is a **separate, pure-Java gate**, unrelated
to the native library:

- `b/b/a/a/k/c/u.smali` and `.../w.smali` (decompiled Java:
  `MainTypeAdapter`'s click-handler inner classes) each start their
  `onClick` with:
  ```smali
  invoke-virtual {v0, v1, v2}, Lcom/tencent/mmkv/MMKV;->a(Ljava/lang/String;Z)Z
  ; v1 = "ID_abnormal", v2 = true (default)
  move-result v0
  if-eqz v0, :cond_0          ; skip the block (proceed) only if stored value is false
  ; ... else: toast "device disabled" + return, never navigates
  ```
- This preference is only ever set to `false` by a successful device-login
  API response (`bussData.getEnable().equals("0")` — see
  `b/b/a/a/g/c/d.java`, `plans/README.md` for the full trace). If that
  login call hasn't succeeded yet (fresh install, no prior state) or the
  server reports this device as not "enabled" for any reason, this
  preference reads as `true` (its *default*, since the key doesn't exist
  yet) and blocks navigation.
- Same fix pattern as the credit-gate patches in `README.md`: found the
  `if-eqz v0, :cond_0` in both `u.smali` and `w.smali`, changed to
  `goto/16 :cond_0` — unconditionally treat the device as enabled,
  regardless of what MMKV/the server actually says.
- **Verified working**: after this patch, tapping "Smartphones" navigates
  straight to `ClassifyBrandActivity` and shows the full brand list (Apple,
  Samsung, Huawei, Xiaomi, Redmi, OPPO, Vivo, Realme, OnePlus, Tecno,
  Motorola, Lava, ...) — no toast, no block.
- Note: `FilmCutActivity`'s own internal `ID_abnormal` checks (3 places,
  `FilmCutActivity.java:258/672/960`) already default to **`false`** (not
  `true`) when the key is absent — i.e. the actual cutting screen was never
  going to be blocked by this same gate the way the category-list entry
  point was. Left unpatched; only the two navigation-gating adapters needed
  the fix. `SystemInfoActivity`'s display of "O dispositivo está desativado"
  (System Info screen) was left as-is too — purely cosmetic/informational,
  doesn't gate anything, and defaults to `true` there as well (matches the
  adapters, just not wired to a blocking `return`).

## Live test on the physical machine (no material loaded)

With both patches installed, walked through: Settings → Material Settings →
"Teste de corte" → Cutting Test screen (100×130mm test template) →
"Starting Test". Confirmed via `logcat`: `class have find` logged multiple
times with **no `exit`/crash** following — the native bypass holds up
through this real flow, not just the earlier System Info screen.

No physical blade movement was observed. Root cause, from reading
`CutTestActivity.java`: tapping the button only sends a status query
(`"BD:10;"`, see `b/b/a/a/j/a.java:634-636`) over the serial port. The
actual cut only happens if the *mechanism* responds with
`RCMD=10,1;` → `RCMD=10,0;<nonce>;` (triggering our `getHandshake`) →
(app answers) → `RCMD=12,0;` (mechanism confirms) — only then does the app
send the real toolpath data (`onSerialPortEvent`, the `RCMD=12,0;` branch,
~line 127-135). No serial response was seen at all in this attempt (no
`onSerialPortEvent` log line either) — most likely because the mechanism's
own firmware requires a material-presence sensor to trigger before it
begins that handshake sequence at all, which is unrelated to anything
patched here. **Not yet re-tested with actual film loaded** — that is the
next real validation step, deferred until material is available.

## Third blocker: real cuts silently rejected (`getHandshake()` returning fake values)

With both patches above installed, category browsing and the cut-test screen
worked, but an actual cut attempt (real button press, on the physical
machine) always got stuck on **"Obter o status da máquina"** forever, with
zero physical reaction from the mechanism. Ruled out first, each confirmed
independently on the device before finding the real cause:
- **Not** serial-port timing — extended the poll interval (100ms→500ms) and
  the max retry window (7→31 iterations, ~15s total) in
  `b/b/a/a/j/d.smali`/`d$a.smali`. No change.
- **Not** Bluetooth interference — disabled BT entirely (left on from the
  earlier, separate `CUTTER_E326` BT-radio investigation, see
  `hardware-re/cutter-e326-bridge/BLUETOOTH_INVESTIGATION.md`). No change.
- **Not** a stuck mechanism/firmware state — full physical power cycle of the
  machine, including unplugging the USB-OTG cable (requiring the
  RECOVERY-pin root trick to be redone from scratch). No change, identical
  symptom.

### Finding the real cause: live serial capture

Hooked `SerialPortHelp.g([B)` (raw write) and `FileInputStream.read`/
`FileOutputStream.write` with Frida (`hook_serial.js`, attached via
`run_hook.py`) during a real button-press attempt. Captured the exact
exchange:

```
app  -> BD:10;
mech <- RCMD=10,1;                     (busy, app retries)
mech <- RCMD=10,0;RCMD=11,<nonce>;     (ready, sends nonce)
app computes JniUtils.getHandshake(nonce), sends:
app  -> BD:12,<value>;
mech <- RCMD=12,1;                     (REJECTED — app only treats
                                         RCMD=12,0; as success, so it
                                         silently retries forever)
```

Reproduced identically across two independent captures (before and after
the power cycle above), ruling out timing/state as the cause. The rejection
is specifically of the **content** of `getHandshake()`'s output, not the
protocol framing (the exchange up to that point is byte-for-byte correct).

### Root cause: `getHandshake()` degrades to a trivial echo when the anti-tamper check fails

Direct comparison, same input nonce, via Frida (`JniUtils.getHandshake(123456)`):

| Build | Result (raw bytes, ASCII) |
|---|---|
| **Stock**, unmodified app (tested earlier in this project, before any patching) | `BD:12,14885604;` — a real, non-trivial transformed value |
| **DragX**, with only the `JNI_OnLoad` exit()-bypass patch above | `BD:12,123456;` — **the input nonce echoed back verbatim** |

The native library isn't crashing anymore, but it's returning garbage: a
value that is trivially just `"BD:12," + nonce + ";"`, not a real computed
signature. The physical mechanism correctly detects this isn't a valid
signed response and rejects it (`RCMD=12,1;`) — which fully explains the
"Obter o status da máquina" freeze. **The `JNI_OnLoad` patch fixed the
crash but did not fix the crypto** — it turns out `FUN_0002232c` (the
function that patch bypasses the *caller's* check on) has its own internal
logic that must genuinely succeed for `getHandshake()` to compute real
values, not just avoid the `exit(0)`.

### Decompiling `FUN_0002232c` itself

Previously only its caller (`JNI_OnLoad`) had been examined — its own body
had been left as a black box since bypassing the caller's check on its
*return value* was sufficient for the crash fix. Decompiling it directly
(`DecompileFun2232c.java`, same headless Ghidra technique as above) showed a
heavily control-flow-flattened function that calls through the **JNIEnv
function-pointer table** (`(**(code**)(*param_1 + <offset>))(param_1, ...)`
— standard JNI vtable-call codegen) to reach Java reflection APIs.

The function references ten short byte blobs (`DAT_000434e0` etc.) passed
as C-string arguments to these calls — not plaintext, XOR-obfuscated. XOR
key varies per string but is always a single repeating byte, recoverable
by guessing 2-3 expected leading characters (e.g. Java signatures reliably
start with `(` / `L`) and XORing against the known plaintext:

| Address | Key | Decoded string |
|---|---|---|
| `0x434e0` | `0x4a` | `getPackageManager` |
| `0x43500` | `0x87` | `()Landroid/content/pm/PackageManager;` |
| `0x43526` | `0x55` | `getPackageName` |
| `0x43540` | `0x5f` | `()Ljava/lang/String;` |
| `0x43555` | `0x16` | `getPackageInfo` |
| `0x43570` | `0xf2` | `(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;` |
| `0x435a6` | `0x77` | `signatures` |
| `0x435c0` | `0x3d` | `[Landroid/content/pm/Signature;` |
| `0x435e0` | `0xcf` | `toCharsString` |
| `0x435f0` | *(not decoded — very long, likely the hardcoded expected cert hex)* | — |

Dumped via a small Ghidra script that reads raw bytes at each address
(`DumpHex2232c.java`), decoded by hand (XOR each byte against the constant
key once found).

This fully identifies the function: it retrieves the running app's own
signing certificate —
`context.getPackageManager().getPackageInfo(getPackageName(), GET_SIGNATURES).signatures[0].toCharsString()`
— and `strcmp()`s the resulting hex string against a hardcoded constant
(the **vendor's own certificate hash**, baked into the `.so` at build time).
Since DragX is resigned with our own self-signed key
(`dragx-release.keystore`), this comparison always fails on our build — and
apparently some later code, gated on this same success/failure, decides
whether `getHandshake()` performs the real signing math or falls back to
the trivial echo. (The exact mechanism of *how* the fallback is chosen
inside `getHandshake()` itself was not traced — patching the check itself,
below, made that unnecessary.)

### The patch

Located the exact `strcmp()` call site in the disassembly (Ghidra address
`0x000228d4`):

```
000228cc  ldr r0,[0x00022af0]     ; r0 = &DAT_000435f0 (expected/vendor cert hex, PC-relative)
000228d0  ldr r1,[sp,#0x28]       ; r1 = local_30 (our actual, resigned cert hex)
000228d2  add r0,pc
000228d4  blx 0x0001bcf8          ; <<< PATCHED: strcmp(r0, r1) -> forced to 0
000228d8  clz r0,r0               ; (downstream: converts strcmp result to a 0/1 flag)
```

Found by dumping the raw disassembly of the whole function
(`DumpAsmFun2232c.java`) and matching the decompiled line
`iVar8 = strcmp((char *)&DAT_000435f0,local_30);` against the `blx` call
sitting at the equivalent position. **File offset located by byte-sequence
search, not offset arithmetic** — searched the actual `.so` file for the 20
raw bytes surrounding the `blx` instruction
(`b8e70c998848 0a910a99 7844 f9f710ea b0fa80f0`) and found exactly one
match, at file offset `0x128d4` (the `blx` itself is the 4 bytes at
`0x128d4`: `f9 f7 10 ea`). This is consistent with the `0x100000` image-base
convention noted above (`0x228d4 − 0x100000 = 0x128d4`), but was verified
directly against file bytes rather than trusted blindly — same discipline
as the first patch, and worth repeating for *any* future patch in this
binary before touching bytes.

Patched those 4 bytes from `f9 f7 10 ea` (`blx 0x0001bcf8`, the real call to
`strcmp`) to `00 20 00 bf` (`movs r0, #0` ; `nop`) — Thumb-2 encoding,
2 instructions filling the same 4-byte slot. This makes the call site set
`r0 = 0` directly instead of calling `strcmp` at all: `r0 = 0` is exactly
what `strcmp()` returns for equal strings, so every downstream check that
reads "did the signature match" now unconditionally sees "yes", regardless
of what our real (resigned) certificate actually is. The real
`getPackageManager()`/`getPackageInfo()`/`toCharsString()` calls before it
still run normally (their results are just never compared against anything
meaningful anymore) — minimal, single-purpose patch, same philosophy as the
`JNI_OnLoad` patch above.

Applied with a small Python script (reads the file, asserts the expected
original 4 bytes at `0x128d4` before writing — fails loudly rather than
silently patching the wrong location if ever rerun against a different
vendor build) to
`decoded/lib/armeabi-v7a/libnewcutjni.so`, then rebuilt
(`apktool b decoded -o DragX-unsigned-v2.apk`), resigned with the existing
`dragx-release.keystore`, reinstalled.

**Verified working**: `JniUtils.getHandshake(123456)` on the newly patched,
running process now returns `BD:12,14885604;` — **byte-for-byte identical**
to the stock, unmodified app's output for the same input, confirming the
real cryptographic computation is restored. Machine handshake completes
(`RCMD=12,0;` accepted, no more "Obter o status da máquina" freeze), and a
**real physical cut succeeded** on the machine. This is the fix that made
actual cutting work, on top of everything else in this document.

## Files changed (on top of what's in `README.md`)

- `decoded/lib/armeabi-v7a/libnewcutjni.so` — two separate binary patches to
  the same file:
  1. File offset `0x160ee` (Ghidra address `0x260ee`), `04bf` → `00bf` —
     bypasses the `JNI_OnLoad` crash (`exit(0)`).
  2. File offset `0x128d4` (Ghidra address `0x228d4`), `f9f710ea` →
     `002000bf` — bypasses the certificate/signature check inside
     `FUN_0002232c` that gates whether `getHandshake()` computes real
     crypto or a trivial fallback. **This is the patch that makes real
     cutting work** — without it, the app runs fine but every handshake
     with the physical mechanism is silently rejected.
- `decoded/smali/b/b/a/a/k/c/u.smali` — `if-eqz v0, :cond_0` →
  `goto/16 :cond_0` (one occurrence).
- `decoded/smali/b/b/a/a/k/c/w.smali` — same change (one occurrence).

Both native patches are asserted-then-applied via short Python scripts
(check exact original bytes at the exact offset before writing) rather than
a blind hex editor — reapply this way on any other machine's `.so` if the
firmware version differs and offsets need to be re-verified (see
`README.md` → "Deploying to other machines").
