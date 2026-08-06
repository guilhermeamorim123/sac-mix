# CUTTER_E326 Bluetooth investigation (started, not resolved)

## Why this started

Owner recalled seeing someone control a similar cutting machine using just a
phone + Bluetooth (no root, no touching the machine's internals). Worth
checking because if real, it would be a much simpler deployment path than
the root + APK-replace process documented in `README.md`/`NATIVE_PATCH.md`.

## What's confirmed

- The Upprinting/DragX APK (V7.0.3.005) declares **zero Bluetooth
  permissions** in its manifest — the app itself never uses Bluetooth for
  anything. Whatever the owner saw is not this app version doing it.
- The machine's Android board (RK3126C tablet) has Bluetooth hardware
  (`android.hardware.bluetooth` + `bluetooth_le` features present), but it's
  **off by default** and its own name shows as generic `rksdk` (not
  `CUTTER_E326`) — this is the tablet's own radio, unrelated to the finding
  below.
- **A second, independent Bluetooth radio exists**: scanning from the
  tablet's own Bluetooth (enabled via Settings → Bluetooth →  toggle on,
  `am start -a android.settings.BLUETOOTH_SETTINGS` + `input tap` on the
  toggle at roughly (655,126) in portrait) reveals a nearby device named
  **`CUTTER_E326`**, MAC `00:16:A6:01:75:2B` — this matches the Bluetooth
  name noted in the very first hardware-ID pass of this whole project. This
  confirms the *cutting mechanism itself* (or some board other than the
  Android tablet) has its own Bluetooth radio, separate from everything
  we've worked with all session.
- **Pairing works**: tapping the device prompts a PIN dialog ("Geralmente,
  0000 ou 1234"). **PIN `1234` succeeds** — device moves from "Dispositivos
  disponíveis" to "Dispositivos pareados". `0000` was tried first and
  failed.
- This is **Bluetooth Classic** (BR/EDR), not BLE-only — it uses the legacy
  PIN-pairing dialog, not a BLE bonding flow.

## What's blocked

Opening an actual **RFCOMM data channel** to the paired device fails in
every combination tried, always after a suspiciously uniform **~60 second**
Android-side timeout (looks like a platform default, not something
channel/device-specific):

- `BluetoothDevice.createRfcommSocketToServiceRecord(SPP_UUID)` (standard
  Serial Port Profile UUID `00001101-0000-1000-8000-00805F9B34FB`), secure
  variant → fails after ~60s:
  `IOException: read failed, socket might closed or timeout, read ret: -1`
  (thrown inside `BluetoothSocket.connect()` → `waitSocketSignal` →
  `readAll`).
- Same UUID, **insecure** variant (`createInsecureRfcommSocketToServiceRecord`)
  → identical failure, identical ~60s timing.
- Bypassing SDP entirely with the hidden `createRfcommSocket(int channel)`
  API, tried channels **1 through 5** individually → every single one fails
  identically at ~60s (channel 5 at 55s, close enough to be the same
  timeout hitting mid-attempt).

`logcat` during a connect attempt shows real low-level BT stack activity
(not an instant/local failure):
```
bt_l2cap: l2cu_adjust_out_mps bad packet size: 0  will use MPS: 0
bt_sdp  : process_service_search_attr_rsp
... (30+ seconds later) ...
bt_rfcomm: port_rfc_closed RFCOMM connection in state 1 closed: Peer connection failed (res: 16)
```
So the connection attempt is genuinely reaching the remote device / going
through real protocol exchange (SDP responds), but the RFCOMM channel never
actually completes, regardless of security mode or channel number. This
rules out "wrong channel number" as the simple explanation — every channel
fails the exact same way.

## Leading hypotheses for what to try next (untested)

1. **It's BLE (GATT), not Classic RFCOMM, for actual data.** Classic
   pairing succeeding (PIN dialog) doesn't guarantee the *data* channel is
   RFCOMM — some dual-mode chips use Classic only for pairing/discoverability
   and expose the actual control interface via BLE GATT services/
   characteristics instead. Worth scanning for BLE services on this same MAC
   (`BluetoothGatt` APIs) rather than assuming SPP.
2. **A specific initiation sequence/companion app requirement.** Cheap
   Bluetooth serial bridges sometimes only accept a connection from a
   specific paired "master" or need a wake-up sequence first. Without a
   reference implementation (the owner's remembered companion app) to
   sniff, this is hard to guess blindly.
3. **`android.bluetooth.BluetoothHciSnoopLog`** — Android can capture a full
   HCI snoop log (`persist.bluetooth.btsnoopenable` / Developer Options →
   "Enable Bluetooth HCI snoop log"). If a *known-working* phone+app pairing
   with this exact machine is ever available again, capturing that log and
   analyzing it in Wireshark would show the exact protocol/UUID/channel used
   — far more reliable than continuing to guess blindly from this side.

## How to resume

- Device stays paired (`00:16:A6:01:75:2B`, PIN `1234`) — no need to redo
  pairing.
- Test scripts: `BtProbe.java` (secure SPP + send a wired-protocol-style
  probe string), `BtProbe2.java` (insecure SPP, passive listen only),
  `BtProbe3.java` (channel 1–5 sweep, hidden `createRfcommSocket(int)` API).
  All three follow the same pattern established earlier in this project:
  plain Java using reflection against `android.bluetooth.*` framework
  classes (no native libs, no android.jar needed to compile), run via
  `app_process` as root — same toolchain as `frida_bridge.py`'s
  `ActivityThread` trick.
- Each failed connect attempt costs ~60 real seconds — budget accordingly
  before trying more channels/variants in one sitting.
