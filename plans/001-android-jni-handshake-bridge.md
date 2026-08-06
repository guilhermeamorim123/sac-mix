# Plan 001: On-device `app_process` JNI bridge exposes `getHandshake()` over local TCP

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: this plan was written against static analysis
> of a decompiled APK, not a git-tracked source tree, so there is no SHA diff
> to run. Instead, re-verify the two facts this plan depends on before
> starting Step 1:
> 1. `adb devices` shows the RK3126C device as `device` (not `unauthorized`/`offline`).
> 2. `adb shell "su -c id"` returns `uid=0(root)`.
>
> If either fails, STOP — the root-access method (shorting the `RECOVERY`
> header pins during boot) needs to be redone first; that is outside this
> plan's scope.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (writes/runs new code on the physical machine's Android
  filesystem via adb; no risk to the CoS vault or any other project)
- **Depends on**: none
- **Category**: tech-debt / migration (unblocks replacing the vendor app)
- **Planned at**: commit `be97d1d`, 2026-07-01 (of the `Chief of Staff` vault
  repo — the audited target itself is a decompiled APK, not a git repo; see
  "Current state" for its own identifying facts instead of a SHA)

## Why this matters

The CUTTER_E326 machine refuses to execute cut commands from anything but the
stock `cn.upus.app.upprinting` Android app, because the serial handshake step
(`RCMD=10,0;<nonce>` → response) requires computing a value via
`libnewcutjni.so`'s native `getHandshake(long nonce)`, which is RSA-backed and
not something worth reverse-engineering byte-for-byte. We already have root
on the machine (via the `RECOVERY`-pin boot trick). The fastest, lowest-risk
way to obtain correct handshake responses without cracking the crypto is to
run a tiny helper *on the machine itself*, inside a real Android runtime, that
calls the vendor's own native function and hands back the answer over a local
socket. Once this bridge exists and is verified against a live handshake, any
future replacement client (PC-side or on-device) can complete the protocol by
querying this bridge instead of understanding the RSA scheme.

This plan builds and verifies **only the bridge** — not the full replacement
client, not the serial I/O, not the cutting UI. It ends when the bridge can
take a nonce and return the exact same bytes the stock app would have written
to `/dev/ttyS1` for that nonce.

## Current state

Facts gathered from static analysis of the decompiled APK at
`C:\Users\Dvilh\Downloads\Upprinting_decompiled\` (package `cn.upus.app.upprinting`,
versionName `V7.0.3.005`):

- **Native method declarations** — `sources\com\cut\cutjni\JniUtils.java`:
  ```java
  package com.cut.cutjni;

  public class JniUtils {
      static {
          System.loadLibrary("newcutjni");
      }
      public static native char[] cmd_GetPassWordCutChar(String str);
      public static native String convertNumber(String str);
      public static native char[] convertNumber2(ArrayList<String> arrayList, String str);
      public static native String encryptSign();
      public static native byte[] getHandshake(long j2);
  }
  ```
  The bridge only needs to reproduce this exact package/class name and the
  exact native method signatures — the JVM's `RegisterNatives` binds by
  (class, method name, JNI signature), not by which `.java` file declared it.

- **Where `getHandshake` is called from**, e.g.
  `sources\cn\upus\app\upprinting\ui\activity\FilmCutActivity.java:1400-1411`:
  ```java
  if (data.contains("RCMD=10,0;")) {
      String[] strArrSplit = data.split(";");
      String[] strArrSplit2 = strArrSplit[1].split(",");
      if (strArrSplit2.length >= 2 && !TextUtils.isEmpty(strArrSplit2[1])) {
          b(JniUtils.getHandshake(Long.parseLong(strArrSplit2[1])));
      }
  }
  ```
  So the nonce is the second comma-separated field after `RCMD=10,0;`, parsed
  as a `long`. The identical pattern repeats in `CustomCutActivity.java:1497`,
  `setting/CutTestActivity.java:120`, `setting/FactoryTestActivity.java:543`,
  and `setting/MachineConfigActivity.java:419` — confirms this is the one
  call site shape across the whole app, not activity-specific behavior.

- **How the response is sent back** —
  `sources\cn\upus\app\upprinting\base\BaseDataBindingActivity.java:291-294`:
  ```java
  public void b(byte[] bArr) {
      b.b.a.a.j.d dVarD = b.b.a.a.j.d.d();
      dVarD.f358f.execute(dVarD.new a(bArr));
  }
  ```
  which ends up in `sources\b\b\a\a\j\d.java:300-315` (`SerialPortHelp.g`):
  ```java
  public boolean g(byte[] bArr) {
      OutputStream outputStream = this.f354b;
      if (outputStream != null) {
          outputStream.write(bArr);
          this.f354b.flush();
      }
      return false;
  }
  ```
  **The raw byte array from `getHandshake()` is written straight to the
  serial port** — no `RCMD=...;` text wrapping, no extra framing. This bridge
  must preserve that: hand back exactly what the native function returns.

- **The native library is NOT dlsym-able for the functions we need.**
  Verified directly against the shipped `.so` in this session:
  ```
  $ readelf -W --dyn-syms resources\lib\armeabi-v7a\libnewcutjni.so | grep Java_com_cut_cutjni
  653: 00014bbd  3536 FUNC GLOBAL DEFAULT 13 Java_com_cut_cutjni_JniUtils_convertNumber2
  751: 00014385  2104 FUNC GLOBAL DEFAULT 13 Java_com_cut_cutjni_JniUtils_convertNumber
  ```
  Only `convertNumber`/`convertNumber2` are plain exported symbols.
  `getHandshake`, `encryptSign`, and `cmd_GetPassWordCutChar` do not appear —
  `JNI_OnLoad` (present at offset `0x15fd5`, size 1004 bytes) must register
  them dynamically via `RegisterNatives()`. A bare C program calling
  `dlopen()` + `dlsym()` on those three names **will get `NULL`** — there is
  nothing to look up. The only way to reach them is a genuine `JNIEnv*` from
  a running ART/Dalvik VM, i.e., run inside an actual Android process. This
  plan uses `app_process` (Android's built-in way to launch a class with a
  full ART runtime from the shell — no Android Studio/APK build required) for
  exactly this reason.

- **RK3126C is 32-bit ARM (Cortex-A7)** → use
  `resources\lib\armeabi-v7a\libnewcutjni.so`, not the `arm64-v8a` copy.

- **Device state**: root already obtained (see `CLAUDE.md`/session context —
  short-circuiting the 2-pin `RECOVERY` header during boot exposes a
  pre-authorized `adb`). `adb root` works without restriction (userdebug
  build). Tools already installed per prior session:
  `C:\Users\Dvilh\platform-tools\` (adb/fastboot), `C:\Users\Dvilh\jadx-cli\`,
  Java 17 (Temurin).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Confirm device | `adb devices` | one line, state `device` |
| Confirm root | `adb shell "su -c id"` | `uid=0(root) gid=0(root)...` |
| Push files | `adb push <local> /data/local/tmp/` | `1 file pushed...` |
| Run bridge | `adb shell "su -c 'app_process -Djava.class.path=/data/local/tmp/bridge.jar /data/local/tmp com.cut.bridge.Bridge'"` | prints `listening on 127.0.0.1:PORT` and blocks |
| Forward port | `adb forward tcp:8654 tcp:8654` | prints `8654` |
| Java compiler present | `javac -version` | prints a version ≥ 8 |
| DEX compiler present | `d8 --version` (from Android SDK build-tools) or `dx --version` | prints a version; if neither exists, see Step 2 |

## Suggested executor toolkit

- No project-specific skills apply (this is a hardware/Android-native task,
  not a tracked source repo). Standard `adb`/Android tooling only.
- If available, `jadx-gui` (companion to the already-installed `jadx-cli`)
  is useful for double-checking any call site referenced above, but is not
  required to execute this plan.

## Scope

**In scope** (new files only, created under a new directory — nothing in the
decompiled APK or the vault is modified):
- `hardware-re/cutter-e326-bridge/Bridge.java` (new) — the `app_process`
  entry point.
- `hardware-re/cutter-e326-bridge/com/cut/cutjni/JniUtils.java` (new) — a
  clone of the native declarations shown above, package/class name and
  signatures byte-for-byte identical to the original.
- `hardware-re/cutter-e326-bridge/README.md` (new) — build/run instructions
  distilled from this plan, for future reference.
- On the device: files under `/data/local/tmp/` only (`bridge.jar`,
  `libnewcutjni.so`).

**Out of scope** (do NOT touch, even though related):
- Anything under `C:\Users\Dvilh\Downloads\Upprinting_decompiled\` — read
  reference only, never modify or attempt to rebuild/repackage the APK.
- The actual RCMD serial protocol client (reading `/dev/ttyS1`, driving the
  cut sequence) — a separate future plan once this bridge is verified.
- `encryptSign()` / the `cutter.skycut.cn` login flow — unrelated to the
  local machine handshake (see `plans/README.md` "Key findings"); do not
  spend effort wiring it up.
- Any change to `/system/app/Upprinting/Upprinting.apk` on the device, or to
  the running Upprinting app's process — the bridge must be a standalone
  process, not an injection into the vendor app.
- The physical UART0-header tap for true PC-side serial access — a hardware
  task, not a software one, and not needed to verify this bridge (Step 5
  verifies entirely on-device).

## Git workflow

This is a standalone hardware-RE side project, not part of any tracked
application. If the vault's git repo is used to store
`hardware-re/cutter-e326-bridge/`, commit it as a normal commit (no special
branch convention observed for this kind of content); otherwise these files
can just live on disk. Do not push anywhere unless the operator asks.

## Steps

### Step 1: Extract the two files needed from the decompiled/APK tree

Copy (do not move) into a new local working folder:
- `resources\lib\armeabi-v7a\libnewcutjni.so` →
  `hardware-re/cutter-e326-bridge/libnewcutjni.so`

**Verify**: file exists and size is 210548 bytes (`ls -la` /
`Get-Item ... | Select Length`).

### Step 2: Confirm/install a DEX toolchain

You need `javac` (present per Current state) plus something that turns
`.class` into `.dex` (`d8`, shipped in Android SDK `build-tools/<ver>/`, or
the older `dx`). Check:

```
d8 --version
```

If not found, check for an existing Android SDK install
(`%LOCALAPPDATA%\Android\Sdk\build-tools\*\d8.bat` is the common Windows
location) and add it to `PATH` for this session. If no Android SDK is
installed at all, install the **command-line tools only** package from
Android's official SDK, then run `sdkmanager "build-tools;34.0.0"` to fetch
`d8`. Do not install a full Android Studio unless nothing else works.

**Verify**: `d8 --version` prints a version string, exit 0.

### Step 3: Write the cloned native declarations class

Create `hardware-re/cutter-e326-bridge/com/cut/cutjni/JniUtils.java`:

```java
package com.cut.cutjni;

public class JniUtils {
    static {
        System.loadLibrary("newcutjni");
    }
    public static native char[] cmd_GetPassWordCutChar(String str);
    public static native String convertNumber(String str);
    public static native char[] convertNumber2(java.util.ArrayList<String> arrayList, String str);
    public static native String encryptSign();
    public static native byte[] getHandshake(long j2);
}
```

This must match the original in `sources\com\cut\cutjni\JniUtils.java`
**exactly** (package name, class name, method names, parameter/return types)
— `RegisterNatives` inside `JNI_OnLoad` binds by this exact signature, and a
mismatch means the lookup silently fails to bind (native call throws
`UnsatisfiedLinkError` at call time, not at load time).

**Verify**: file compiles standalone —
`javac -d out hardware-re/cutter-e326-bridge/com/cut/cutjni/JniUtils.java`
→ exit 0, produces `out/com/cut/cutjni/JniUtils.class`.

### Step 4: Write the `app_process` bridge entry point

Create `hardware-re/cutter-e326-bridge/Bridge.java` in the default package,
implementing:
1. A `main(String[] args)` that opens a plain `java.net.ServerSocket` bound
   to `127.0.0.1` on a fixed port (suggest `8654` — anything free is fine,
   just keep it consistent with the `adb forward` command above).
2. Accepts one connection at a time (a simple blocking loop is fine — this
   is a debug bridge, not a production service).
3. Protocol: read one line of ASCII text from the client, a decimal integer
   nonce (matching the `Long.parseLong(strArrSplit2[1])` parsing seen in
   `FilmCutActivity.java:1409`). Call
   `com.cut.cutjni.JniUtils.getHandshake(nonce)`. Write back one line: the
   resulting `byte[]` hex-encoded (e.g. `bytesToHex(...)` — plain manual hex
   encoding, no external dependency needed), followed by `\n`. Close the
   per-request stream but keep the server loop running.
4. Print `listening on 127.0.0.1:8654` to stdout right after the socket
   binds, and print each request/response pair to stdout for debugging
   (`recv nonce=<n>` / `send hex=<...>`).
5. Wrap the native call in try/catch; on `UnsatisfiedLinkError` or any
   `Throwable`, print the full stack trace to stdout and reply with the
   literal line `ERROR` instead of crashing the process — a bind failure on
   one request must not kill the bridge for subsequent ones.

**Verify**: `javac -d out hardware-re/cutter-e326-bridge/Bridge.java` → exit
0 (it's fine that this step doesn't yet resolve `com.cut.cutjni.JniUtils` if
compiled alone; compile both files together in Step 5's packaging so the
reference resolves: `javac -d out hardware-re/cutter-e326-bridge/Bridge.java hardware-re/cutter-e326-bridge/com/cut/cutjni/JniUtils.java`).

### Step 5: Package and push to the device

```
javac -d out Bridge.java com/cut/cutjni/JniUtils.java
d8 --output . out/Bridge.class out/com/cut/cutjni/JniUtils.class
# produces classes.dex in the current directory
adb push classes.dex /data/local/tmp/bridge.jar
adb push libnewcutjni.so /data/local/tmp/libnewcutjni.so
```

`app_process` loads native libraries via `System.loadLibrary`, which
searches the standard linker paths plus, on API 23+, whatever is set via
`java.library.path`. Simplest reliable option: also copy the `.so` to a
directory already on the default native library search path for the shell
user, or set `-Djava.library.path=/data/local/tmp` when invoking
`app_process` (see Step 6). If the executor's `app_process`/API level
doesn't honor `-Djava.library.path`, fall back to
`adb push libnewcutjni.so /data/local/tmp && adb shell "su -c 'cp /data/local/tmp/libnewcutjni.so /system/lib/libnewcutjni.so'"` —
**only if `/system` is writable on this build** (it's a `userdebug` build
per the RE notes, so likely yes) — and treat this as a STOP-and-report
condition if `/system` is read-only and `java.library.path` doesn't work
either, rather than trying more invasive remounts.

**Verify**: `adb shell "ls -la /data/local/tmp/bridge.jar /data/local/tmp/libnewcutjni.so"` → both files listed with expected sizes.

### Step 6: Run the bridge and verify against a live handshake

```
adb shell "su -c 'app_process -Djava.library.path=/data/local/tmp -Djava.class.path=/data/local/tmp/bridge.jar /data/local/tmp Bridge'"
```

In a second terminal:
```
adb forward tcp:8654 tcp:8654
printf '123456\n' | nc 127.0.0.1 8654
```
(any `nc`/netcat equivalent works; PowerShell's `Test-NetConnection` does
not send data, use a real TCP client)

**Verify (step A — bridge alone works)**: response is a hex string (not
`ERROR`), and the bridge's own stdout log shows
`recv nonce=123456` / `send hex=<...>` with no stack trace.

**Verify (step B — matches the real device, the actual acceptance test for
this plan)**: with the stock Upprinting app also installed and a real
handshake nonce captured from `/dev/ttyS1` traffic during an actual cut
attempt (e.g. via `adb shell "su -c 'cat /dev/ttyS1'"` run in parallel while
triggering a cut from the app's UI, capturing the `RCMD=10,0;<real nonce>;`
line), feed that **same nonce** to the bridge and confirm the hex response
is byte-identical to what a serial sniff (or the app's own logcat —
`LogUtils.d("一次发完握手数据")` fires right after `getHandshake` is called,
though it doesn't log the bytes; if bytes aren't observable via logcat, add
a temporary `Log.d` call is out of scope — instead rely on functional
verification: if this bridge's response is later fed back into the physical
handshake step and the machine proceeds to `RCMD=12,0;` "handshake success",
that is the real proof). Because this cross-check requires a live cut
attempt on the physical machine, treat it as the final gate the human
operator must confirm interactively — do not mark this plan DONE from
Step 6A alone.

## Test plan

There is no automated test suite for this target (decompiled APK, no build
system). Verification is entirely the manual steps above, run against the
real device:
- Bridge starts without exception (Step 6A).
- Bridge returns a stable, deterministic response for a fixed nonce (call
  it twice with the same nonce, confirm identical hex both times — RSA
  signing over a fixed input should be deterministic if `getHandshake` is a
  pure function of the nonce with no internal randomness; if the two calls
  differ, note this in the report — it changes the design of any future
  client, since it would mean the function isn't a pure/cacheable operation).
- Bridge's response, when used in a live handshake attempt on the physical
  machine, results in the machine emitting `RCMD=12,0;` (handshake success)
  rather than staying silent or repeating `RCMD=10,0;`.

## Done criteria

- [ ] `hardware-re/cutter-e326-bridge/Bridge.java` and
      `hardware-re/cutter-e326-bridge/com/cut/cutjni/JniUtils.java` exist and
      compile together with `javac` (exit 0).
- [ ] `classes.dex` builds via `d8`/`dx` (exit 0).
- [ ] Bridge runs on-device via `app_process` and logs
      `listening on 127.0.0.1:8654` without an immediate crash.
- [ ] A test request over the forwarded TCP port returns a hex string (not
      `ERROR`) for at least one nonce value.
- [ ] Repeating the same nonce twice returns the same hex both times (or the
      report explicitly notes it does NOT, since that's a design-relevant
      finding for whoever builds on top of this).
- [ ] The human operator has confirmed, in a live cut attempt, that feeding
      the bridge's response for the real captured nonce results in
      `RCMD=12,0;` from the machine. (This is the only step requiring
      physical access to the running machine and the operator's judgment;
      everything else is machine-checkable.)
- [ ] No files outside the in-scope list were created/modified
      (`git status` if tracked in the vault repo).
- [ ] `plans/README.md` status row for 001 updated.

## STOP conditions

Stop and report back (do not improvise) if:
- `adb shell "su -c id"` does not return `uid=0` — root has been lost and
  needs the `RECOVERY`-pin procedure repeated; that's outside this plan.
- `System.loadLibrary("newcutjni")` throws `UnsatisfiedLinkError` even after
  trying both the `java.library.path` and `/system/lib` placement options in
  Step 5 — this would mean the native library has additional loading
  requirements not yet understood (e.g. a dependency library missing —
  recall it links `libcrypto.so`/`libssl.so`/`libandroid.so`; confirm those
  exist on-device at a path the linker searches before escalating further).
- The native call binds but throws at call time in a way that suggests the
  cloned `JniUtils` class's method signature doesn't match what
  `RegisterNatives` expects (e.g. `NoSuchMethodError` naming a signature) —
  re-diff the clone against `sources\com\cut\cutjni\JniUtils.java` byte for
  byte rather than guessing at a fix.
- The same nonce produces a *different* hex response on repeated calls with
  no code change — flag this prominently in the report; it means
  `getHandshake` has internal state or randomness (e.g. it may itself embed
  a timestamp, or maintain a counter), which changes the entire design of
  any future client (it can no longer precompute/cache responses).

## Maintenance notes

- Whoever builds the actual RCMD protocol client next: it should treat this
  bridge as a black box reached over `adb forward` + TCP, and must resend the
  request if the bridge process has died (it's a debug-grade single-threaded
  loop, not hardened).
- If the vendor ships a firmware/APK update
  (`PGREADY`/`PGOK` sequence seen in `SerialPortHelp.java`), re-extract
  `libnewcutjni.so` from the new APK and re-verify — the handshake scheme
  could change between versions.
- The out-of-scope UART0 hardware tap (see `plans/README.md`) is the next
  real blocker for a true PC-side client; this bridge only solves the crypto
  half of the problem, not the physical serial access half.
