# CUTTER_E326 / rk3126c handshake bridge

Solves the RSA handshake step (`RCMD=10,0;<nonce>` → machine expects a
specific response) without reverse-engineering the crypto: calls the
vendor's own `libnewcutjni.so` via `com.cut.cutjni.JniUtils.getHandshake(nonce)`
inside the **real, already-running** `cn.upus.app.upprinting` process, using
Frida, and exposes the result over a local TCP socket.

## Why Frida, and why a specific old version

Two other approaches were tried and ruled out before this one worked (full
detail in `plans/README.md` "Execution log"):

1. A standalone `app_process` bridge (in this same folder — `Bridge.java`,
   `com/cut/cutjni/JniUtils.java`) that loads `libnewcutjni.so` directly. It
   gets past library loading and a null-`Context` check (see that file's
   history), but the native code self-kills (`SIGKILL`, no tombstone) right
   after an internal log line `"class have find"` — some check beyond simple
   `Context` existence fails and the process dies silently. Not solved.
2. Frida **17.15.3** (the current release at the time) failed differently:
   `device.attach(pid)` — with no script loaded at all — left the target
   process stuck in ptrace'd/traced state (`state=t` in `ps`), or in some
   runs the target process died outright. This turned out to be a **Frida
   version incompatibility with this old Android 7.1.2 (API 25) device**,
   not vendor anti-tamper: a bare attach with **matched old client/server
   versions** (see below) works cleanly with no side effects.

**Use frida `16.0.19` for both the client (pip) and `frida-server` (device).**
Newer Frida (17.x, confirmed) breaks against this specific old Android/ART
combination. 16.0.19 was the version confirmed working in this session;
nearby 16.x releases would likely also work but haven't been tested.

## Setup

1. Root the device (short the 2-pin `RECOVERY` header during boot with the
   `USB-OTG` cable connected — see the main hardware-RE notes). Confirm:
   ```
   adb devices          # shows the device as `device`
   adb shell id          # uid=0(root)
   ```
   Note: this build's `su` does not support `su -c <cmd>` syntax
   (`su: invalid uid/gid '-c'`) — `adbd` already runs as root, so just run
   shell commands directly, no `su` needed.

2. Install the matched Frida client on the PC:
   ```
   pip install "frida==16.0.19"
   ```
   (`frida-tools` may warn about a version conflict if already installed for
   a newer `frida` — harmless, this project only uses the plain `frida`
   Python library, not the interactive `frida`/`frida-ps`/`frida-ls-devices`
   CLI tools. Those CLI tools also don't work under Git Bash on Windows
   regardless of version — they need a real Win32 console, not Git Bash's
   pty; use plain Python scripts against the `frida` library instead, as
   `frida_bridge.py` does.)

3. Download the matching `frida-server` for `android-arm` (this device is
   32-bit ARMv7, NOT arm64) and push it:
   ```
   curl -sSL -o frida-server.xz "https://github.com/frida/frida/releases/download/16.0.19/frida-server-16.0.19-android-arm.xz"
   python -c "import lzma; open('frida-server','wb').write(lzma.open('frida-server.xz').read())"
   adb push frida-server /data/local/tmp/frida-server
   adb shell chmod 755 /data/local/tmp/frida-server
   ```

4. Launch `frida-server` on the device (leave running in background):
   ```
   adb shell "/data/local/tmp/frida-server -l 127.0.0.1:27042"
   ```

5. Make sure the real app is running (find its actual identity via
   `/proc/<pid>/cmdline` — `ps` shows a custom process label `Cutting`, not
   the package name, since the app sets `android:process`):
   ```
   adb shell monkey -p cn.upus.app.upprinting -c android.intent.category.LAUNCHER 1
   ```

6. Run the bridge (from this directory):
   ```
   python frida_bridge.py
   ```
   It attaches to the running app, loads `agent.js` (a Frida RPC script that
   calls `JniUtils.getHandshake`), and listens on `127.0.0.1:8654`.

7. Query it (same wire protocol the original `app_process`-based bridge
   used): connect, send a decimal nonce + `\n`, read back one line of hex —
   or `ERROR`:
   ```python
   import socket
   s = socket.create_connection(('127.0.0.1', 8654))
   s.sendall(b'123456\n')
   print(s.recv(4096))  # b'42443a31322c31343838353630343b\n'
   ```

## What the response actually looks like

`getHandshake(nonce)` returns **plain ASCII text**, not opaque binary RSA
output. Example: nonce `123456` → hex `42443a31322c31343838353630343b` →
decoded: `BD:12,14885604;`. General shape observed:
`BD:12,<decimal number>;`. The trailing number changes with the nonce but
not by any simple linear formula spot-checked so far (e.g. nonce 123456 →
...885604, nonce 123457 → ...885607 — a delta of 3 for a nonce delta of 1;
nonce 1 → ...696615). **Confirmed deterministic**: the same nonce always
produces byte-identical output across repeated calls. No need to reverse the
formula — this bridge is a working oracle for any nonce a real machine ever
sends.

Recall (see main hardware-RE notes / `plans/001-*.md`): the app writes this
response **raw to the serial port**, no extra `RCMD=` wrapping — whatever
`getHandshake` returns is exactly what goes out over `/dev/ttyS1`.

## Files

- `frida_bridge.py` — the driver: attaches Frida, loads `agent.js`, serves
  the TCP protocol.
- `agent.js` — Frida RPC script (`rpc.exports.gethandshake`) that does the
  actual `Java.perform` / `JniUtils.getHandshake` call inside the target
  process.
- `probe.js` / `probe2.js` — throwaway diagnostic scripts used while getting
  this working (single-shot, print to Frida's message channel instead of
  RPC). Kept for reference; `agent.js` is the one `frida_bridge.py` uses.
- `Bridge.java` / `com/cut/cutjni/JniUtils.java` — the earlier, **blocked**
  `app_process` standalone approach. Kept for reference (it correctly
  solves the "no exported symbol to dlsym" and "no Context" problems even
  though it never got a working response) — superseded by this Frida-based
  approach for actually calling `getHandshake`, but potentially still useful
  reference if a fully standalone (no Frida dependency) solution is wanted
  later.
- `libnewcutjni.so`, `libcrypto.so`, `libssl.so` — copied from the
  decompiled APK's `resources/lib/armeabi-v7a/` (not used directly by the
  Frida approach, which calls the copy already loaded inside the real
  running app — kept here from the earlier `app_process` attempt).

## Next steps (not done here)

This bridge only solves the handshake oracle. Still needed for a full
standalone replacement client:
- Build the actual RCMD serial protocol client (open `/dev/ttyS1` — note the
  real app already holds it open while running, so a standalone client needs
  the stock app stopped, or needs to run this same logic from inside a
  modified version of it), parse `RCMD=10,0;<nonce>;`, call this bridge,
  write the raw response back, and continue the rest of the cut sequence.
- The PC-side UART0 header tap (physical hardware work) if true off-device
  control is wanted — see `plans/README.md` "Key findings".
