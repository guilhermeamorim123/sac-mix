# DragX Web Deployer — Validation Log

## 2026-07-02 — End-to-end deploy flow confirmed against the known machine

**Machine:** the original CUTTER_E326 unit (serial `6S9OZFRLDN`, already rooted, already running a working DragX build with both native patches applied and a real cut previously confirmed on it the same day).

**Not yet done:** full validation on a genuinely *new*, previously-untouched machine. This run reused the already-known-good machine to prove the tool's logic (connect/install/verify) works for real, not to re-validate the DragX build itself (already proven earlier the same day via manual steps).

**Steps performed:**
1. Machine connected via USB, `adb tcpip 5555` issued, confirmed reachable at `192.168.15.13:5555`.
2. Disconnected USB (leaving only WiFi ADB active — the tool assumes exactly one connected device and errors on ambiguity, "more than one device/emulator", if both USB and WiFi are active simultaneously at once).
3. Started `server.py`, sent a real `POST /deploy` request for `192.168.15.13:5555`.

**Result:** `overall_success: true`

```json
{
  "overall_success": true,
  "steps": [
    {"status": "success", "message": "Conectado a 192.168.15.13:5555"},
    {"status": "success", "message": "DragX instalado"},
    {"status": "success", "message": "Processo antigo finalizado"},
    {"status": "success", "message": "JNI_OnLoad crash bypass: OK"},
    {"status": "success", "message": "getHandshake() certificate-check bypass: OK"}
  ]
}
```

Both native-library patches verified correctly by the tool. `adb install -r` (reinstall, preserve data) was used, so the machine's existing app data/state was not wiped — this run reinstalled the byte-identical, already-verified `DragX-signed.apk` over itself.

**Not tested in this run** (already independently confirmed earlier the same day, via manual steps, on this same machine — not repeated here to avoid redundant physical wear): live `getHandshake()` value via Frida, and an actual physical film cut. Both should be re-confirmed the first time this tool is used against a genuinely new machine.

**Known limitation surfaced by this run:** if a machine is reachable via both USB and WiFi ADB simultaneously, `deploy()` fails with "more than one device/emulator" (since `run_adb`'s commands never pass `-s <serial>`, matching the original design's single-connected-device assumption). Operators must ensure only one connection method (USB or WiFi) is active at a time when using this tool. Worth a one-line note in a future README if one gets written for this tool.

## Next validation milestone

Full validation on an actual new, never-before-touched machine: physical root → confirm WiFi ADB reachable with no lingering USB connection → run the Web Deployer → confirm `getHandshake(123456)` returns `BD:12,14885604;` via Frida → confirm a real physical cut.
