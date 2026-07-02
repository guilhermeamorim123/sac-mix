# DragX — rebranded, unlimited-cuts build of the CUTTER_E326 controller app

Same app as `cn.upus.app.upprinting` (Upprinting) V7.0.3.005, same package
name, same signing-key-doesn't-matter approach — rebranded to **DragX** (name
+ launcher icon) and patched to remove the local credit/expiry gate that
blocked cutting once `Saldo`/`BALAQTY` (or the subscription window) ran out.

## Why same package name (`cn.upus.app.upprinting`)

Deliberate choice, not an oversight. Reusing the original package name means
this is — as far as Android and `libnewcutjni.so`'s internal environment
checks are concerned — literally the same app, just with different bytecode
in two methods and different name/icon resources. This sidesteps entirely
the unresolved "self-kill after `class have find`" mystery documented in
`plans/README.md` (a from-scratch app under a new package name would have
reopened that risk with no guarantee of success). The handshake/native-crypto
layer (`JniUtils.getHandshake`, used for the film/material handshake, not for
credits) is untouched — only two Java-level gating checks were patched out.

## What was changed

1. **App identity** (`res/values/strings.xml`): `app_name` → `DragX`.
2. **Launcher icon** (`res/mipmap-*dpi/ic_launcher.webp` and
   `ic_launcher_round.webp`): replaced with the DragX "D+X" logo
   (`C:\Users\Dvilh\Downloads\logo_convertida.png`), letterboxed to square
   and resized per density (48/72/96/144/192 px). Note: this device is
   Android 7.1.2 (API 25), so the adaptive-icon XML
   (`mipmap-anydpi-v26/ic_launcher.xml`) is never used at runtime — only the
   legacy per-density `.webp` files matter here. Those files actually contain
   plain PNG-encoded bytes (Android's bitmap decoder sniffs the real file
   header, not the extension) — simpler than re-encoding to true WebP.
3. **Splash screen background** (`res/drawable-xhdpi/bg_img.png`, used by
   `InitActivity`'s layout `layout_activity_init.xml` as
   `android:background`): replaced the stock blue-gradient graphic with a
   dark background + the DragX logo (color-inverted to white-on-transparent
   so it reads on a dark background, composited in the upper-middle area so
   it doesn't collide with the vertically-centered loading spinner/text
   below it). Note this device has no normal Android launcher/home screen —
   `StartActivity` (transparent/translucent theme) immediately hands off to
   `InitActivity`, so *this* screen, not a home-screen icon, is what's
   visible whenever the device returns to its idle/boot state — worth
   rebranding for that reason even though it's easy to miss at first (it has
   no app label text of its own, so before this change it could look like
   the app had "reverted" to stock, even though the installed package/label/
   icon were correct the whole time — confirmed via the recent-apps switcher,
   which does show "DragX" + icon correctly).
   Known cosmetic imperfection (left as-is per operator's call): the source
   logo file's white page background got inverted to black along with
   everything else, so the logo currently sits inside a visible black
   rectangle rather than blending seamlessly into the dark background. Fix
   later by stripping that white background to transparent before inverting,
   if wanted.
4. **Credit gate removed** — `smali/cn/upus/app/upprinting/ui/activity/FilmCutActivity.smali`
   and `.../CustomCutActivity.smali`, each in two places:
   - The pay-per-cut balance check (originally `if (this.y < 1) { toast
     "insufficient balance"; return; }` in the Java decompilation,
     `FilmCutActivity.java:984` / equivalent in `CustomCutActivity.java`):
     the smali `cmp-long` + `if-gez v0, :cond_N` was changed to an
     unconditional `goto/16 :cond_N`, so the low-balance branch is never
     taken regardless of the stored value.
   - The subscription/expiry check (the `else` branch of the same `if/else`
     in the Java source, gating on `cutEndTime < cutCurrentTime`): same
     pattern, same fix — `if-gez v0, :cond_N` → `goto/16 :cond_N`.
   - Both checks converge to the same `:cond_N` label in each file (confirmed
     by reading the surrounding smali), so this is a safe, minimal,
     single-instruction change per site — nothing else in the method needed
     to move.
   - **Not changed**: the balance/quantity *display* and the decrement logic
     in `c0()` (`FilmCutActivity.java:845-861`) still run and still write
     decreasing `BALAQTY`/`USEQTY` values to local SharedPreferences. This
     was deliberate — only the *gate* was removed, not the bookkeeping. The
     on-screen "Saldo" number will still count down (potentially going
     negative) after this patch; it just no longer blocks cutting. If a
     cosmetic "always show unlimited" fix is wanted later, that's a separate,
     optional change to the display code, not needed for the actual goal
     (unlimited cuts).

## How the credit/expiry gate was found

Confirmed via reading `FilmCutActivity.java` (from the `jadx` decompilation
at `C:\Users\Dvilh\Downloads\Upprinting_decompiled\`) that the entire
credit/expiry system — `RCMD=20,...` (mentioned in the machine's own status
messages) notwithstanding — is enforced **purely client-side**: `BALAQTY`
(balance) and `USEQTY` (used count) are read/written to local
`SharedPreferences` (`f.a().f912b...`), and the only check that blocks a cut
is the in-app `if (this.y < 1)` / expiry-window comparison. No server
round-trip, no check from the cutting mechanism's own firmware. This is why
patching the app was sufficient and no hardware/firmware work was needed for
this goal.

## Build process (reproducible)

Tools used (all downloaded fresh this session, see also
`hardware-re/cutter-e326-bridge/README.md` for the JDK/D8 paths):
- `apktool` 3.0.2 (`https://github.com/iBotPeaches/Apktool/releases/download/v3.0.2/apktool_3.0.2.jar`)
- JDK 17 (`C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot\bin\`) for
  `java`, `keytool`, `jarsigner`
- Python + Pillow (already installed) for icon resizing

```
# 1. Decode
java -jar apktool.jar d -f -o decoded Upprinting_V7.0.3.005.apk

# 2. Edit resources/smali (see "What was changed" above)

# 3. Rebuild
java -jar apktool.jar b -o DragX-unsigned.apk decoded

# 4. Sign (self-signed key generated for this project; v1/jarsigner scheme
#    is sufficient for this old Android 7.1.2 target — no need for apksigner
#    v2/v3 schemes)
keytool -genkeypair -v -keystore dragx-release.keystore -alias dragx \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass dragx123456 -keypass dragx123456 \
  -dname "CN=DragX, OU=DragX, O=DragX, L=Unknown, ST=Unknown, C=BR"

jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore dragx-release.keystore -storepass dragx123456 \
  -signedjar DragX-signed.apk DragX-unsigned.apk dragx
```

`dragx-release.keystore` (password `dragx123456`) is the signing key — keep
it if you want to install *updates* to this same app later (Android requires
the same signing key to update an already-installed package; losing this
keystore means any future version needs the same
remove-system-app-then-reinstall dance below, not a normal update).

## Install (this device — already done this session)

Because the stock app was pre-installed as a **system app**
(`/system/app/Upprinting/Upprinting.apk`), and Android requires matching
signatures to update an already-installed package, the stock system APK had
to be removed first (not just `pm uninstall`, which only removes user-level
updates over a system app, not the system app itself):

```
adb root
adb shell am force-stop cn.upus.app.upprinting
adb remount
adb pull /system/app/Upprinting/Upprinting.apk Upprinting-system-backup.apk   # backup, keep it
adb shell rm /system/app/Upprinting/Upprinting.apk
adb reboot
# wait for boot (adb wait-for-device + poll `getprop sys.boot_completed`)
adb install -r DragX-signed.apk
```

Result: installs as a normal **user** app (not system) under the same
package `cn.upus.app.upprinting`, label "DragX", DragX icon. Confirmed
working this session: installs cleanly, launches through
`StartActivity → InitActivity → MainActivity` with no crashes, opens
`/dev/ttyS1` normally (same serial behavior as the stock app), system
permission dialogs correctly show "DragX" as the app name.

**Backup**: `Upprinting-system-backup.apk` (pulled from `/system/app/` before
deletion) — restore path if ever needed: remount `/system` rw, push it back
to `/system/app/Upprinting/Upprinting.apk`, reboot. The original signing key
(vendor's, unknown to us) means DragX and the original can never both be
installed as updates of each other — it's always "remove one, install the
other fresh."

## Deploying to other machines (the actual goal — "sua marca" on other units)

For another physical machine of the same model (RK3126C-based CUTTER_E326 /
same firmware): same steps — root it (short the `RECOVERY` header pins
during boot, see main hardware-RE notes), remove the stock system APK,
reboot, `adb install DragX-signed.apk`. `DragX-signed.apk` and
`dragx-release.keystore` in this folder are the reusable artifacts; no need
to redo the apktool/patch step per machine, only the install step.

For a genuinely **new** machine (never onboarded before), `onboard-new-machine/`
automates this whole flow end-to-end — WiFi ADB setup, DragX deploy, and a
boot-partition patch so the machine never needs a physical USB connection
again. See `onboard-new-machine/README.md`. For routine re-deploys on an
already-onboarded machine, use `hardware-re/dragx-web-deployer/` instead.

**Important — verify the two native-library patches still apply before
trusting a real cut on a *different* firmware version.** `DragX-signed.apk`
bakes in two binary patches to `libnewcutjni.so` at fixed file offsets (see
`NATIVE_PATCH.md`): the `JNI_OnLoad` crash bypass (offset `0x160ee`) and the
certificate-check bypass that makes `getHandshake()` compute real values
(offset `0x128d4` — **this is the one that actually enables cutting**, not
just app stability). Those offsets are only valid for this exact
`libnewcutjni.so` build (from `Upprinting_V7.0.3.005.apk`). If a future
machine ships a different app/firmware version:
1. Pull its `libnewcutjni.so` and diff/checksum it against
   `decoded/lib/armeabi-v7a/libnewcutjni.so` in this folder — if identical,
   the existing `DragX-signed.apk` is safe to install as-is.
2. If different, re-run the same procedure from scratch: decompile with
   headless Ghidra (scripts in `tools/` — `DecompileJniOnLoad.java`,
   `DecompileFun2232c.java`, `DumpAsmFun2232c.java`, `DumpHex2232c.java`),
   locate `JNI_OnLoad`'s check on `FUN_0002232c` and the `strcmp()` call
   inside `FUN_0002232c` itself (search for the same surrounding byte
   patterns documented in `NATIVE_PATCH.md`, don't assume the same
   offsets), patch with `tools/apply_native_patches.py` (edit the offsets
   if they moved — the script asserts the original bytes first and aborts
   loudly if they don't match, so it's safe to try), rebuild, resign with
   the same `dragx-release.keystore`, and **verify with the same Frida
   `getHandshake(123456)` test** (`tools/run_hook.py` +
   `tools/hook_serial.js` for live serial capture if needed, or a short
   ad-hoc Frida script calling `JniUtils.getHandshake(123456)` directly —
   expect `BD:12,14885604;`; if you get `BD:12,123456;` the
   certificate-check patch didn't take, and the machine will reject every
   real cut with `RCMD=12,1;` even though the app looks fully functional
   otherwise).
3. Only trust "it installs and the UI works" as proof the app is ready —
   always confirm the `getHandshake` value before handing a newly-deployed
   machine over for real use, since the broken-crypto failure mode is
   silent (no crash, no error toast, just an infinite "Obter o status da
   máquina" freeze whenever someone actually tries to cut).

## Files

- `decoded/` — apktool-decoded project (smali + resources), the patched
  source of truth, **including both native-library patches** (see
  `NATIVE_PATCH.md`). Re-run `apktool b` here after any further edit.
- `DragX-unsigned.apk` — rebuilt, unsigned. Stale (v1, missing the second
  native patch) — rebuild from `decoded/` if you need a fresh unsigned copy.
- `DragX-signed.apk` — **the artifact to install.** Includes both native
  patches (crash bypass + certificate-check bypass) — confirmed making real
  cuts work on the physical machine.
- `DragX-signed-v1-broken-handshake.apk` — kept only for reference/history.
  Has the `JNI_OnLoad` crash fix but **not** the certificate-check fix — app
  runs fine, UI works, but every real cut silently fails
  (`getHandshake()` returns garbage, machine rejects the handshake forever).
  **Do not deploy this one.**
- `dragx-release.keystore` — signing key (password `dragx123456`). Back this
  up somewhere durable — losing it blocks future in-place updates.
- `Upprinting-system-backup.apk` — original stock system APK, pulled from
  this device before removal, in case of rollback.
- `tools/` — reusable scripts for replicating the RE work on a different
  firmware build: Ghidra headless scripts (`Decompile*.java`, `DumpAsm*.java`,
  `DumpHex*.java`, `DumpStrings2232c.java`), `apply_native_patches.py`
  (applies both binary patches with an assert-first safety check),
  `run_hook.py` + `hook_serial.js` (Frida live serial-traffic capture, used
  to diagnose the `RCMD=12,1;` rejection in the first place).

## Data survival after remove-system-app-then-reinstall (important, learned the hard way)

Removing the stock system APK + rebooting + `adb install -r` **does wipe**
the app's local `/data/data/cn.upus.app.upprinting/` (confirmed: every file
in there dates to the reinstall moment, nothing older survived) — so don't
count on local SharedPreferences/databases surviving this procedure on a
future machine.

**This turned out not to matter for the device catalog** ("3000+ modelos de
corte" for iPhone/Samsung/etc., browsable as Smartphones/Tablets/Navegador
automotivo/... categories from the main screen): that catalog is fetched
live from the vendor's server, not cached in a local app database (checked —
no matching `.db` file exists locally beyond third-party SDK caches like
`AndroidAria.db`/`ua.db`/`umeng_zero_cache.db`, none of which hold catalog
data). It reappeared automatically within seconds of the first post-install
launch, no action needed.

**Why the catalog could re-sync despite losing local data**: the device
identity string (`DEVNO`, shown on the main screen as "Número do
dispositivo" — `DX605241023104125` for this unit) is **not stored only in
app data** — `config.xml` in `shared_prefs` had the correct value again
immediately after the fresh install, meaning the app derives/recovers it from
something persistent outside its own `/data/data` sandbox (never found a
`DEVNO`-setter in the decompiled sources — it's read-only from the app's own
perspective, likely factory-provisioned into a system property, a persistent
partition, or similar). As long as that survives, the vendor server
recognizes the device and re-serves its catalog/entitlements regardless of
the Android-side app data being wiped.

**Practical implication for future machines**: don't panic if the catalog
looks empty right after installing DragX on a new unit — give it a few
seconds on a working network connection to re-sync, same as happened here.
If it genuinely doesn't come back on some unit, that would point at DEVNO
*not* surviving on that particular hardware/firmware variant — worth
re-checking `shared_prefs/config.xml` for a `devno` value before assuming
anything is actually lost.

## Update: native anti-tamper crash found and fixed (see `NATIVE_PATCH.md`)

After the fixes above, actually using the app (Settings → System Info →
"Detecção de rede", and tapping any product category) triggered a
**deliberate native `exit(0)`** inside `libnewcutjni.so`'s `JNI_OnLoad` —
present because the APK is resigned with our own key rather than the
vendor's. Root-caused with headless Ghidra (no GUI available in this
environment) and fixed with a 2-byte binary patch that neutralizes the
pass/fail branch of the check, without needing to know what it actually
checks. A second, unrelated pure-Java gate ("device disabled" blocking
category navigation) was also found and patched the same way the credit
gate was. Both are verified working on-device. **Full technical writeup,
the Ghidra scripts, and exact patch bytes: `NATIVE_PATCH.md` in this same
folder.**

## Update 2: real cuts were silently rejected — second native patch required

The fix above stopped the crash, but real cut attempts still got stuck
forever on **"Obter o status da máquina"**, with zero physical reaction.
Root cause (full writeup in `NATIVE_PATCH.md`): `FUN_0002232c` — the same
function whose *caller* was patched above — performs its own internal
**APK signature verification** (reads the running app's own signing
certificate via `PackageManager`, compares it against the vendor's
hardcoded certificate hash). Since DragX is resigned with our own key, this
always failed, and `JniUtils.getHandshake()` silently fell back to
returning the input nonce echoed back instead of a real computed value —
which the physical mechanism correctly rejects (`RCMD=12,1;`), explaining
the freeze. No crash, no error message — the app looked completely normal
while quietly sending garbage handshake responses.

Fixed with a second, equally minimal binary patch (`libnewcutjni.so`, file
offset `0x128d4`): replaced the `strcmp()` call that performs the
certificate comparison with an instruction that just sets the result to
"match" directly, so the check always passes regardless of what our actual
resigned certificate is. Verified via Frida: `getHandshake(123456)` now
returns the exact same value the untouched stock app returns for the same
input. **A real physical cut succeeded on the machine after this patch —
confirmed by the operator.** Current `DragX-signed.apk` in this folder
already includes both native patches.

## Not done / open follow-ups

- ~~Not yet verified with an actual physical cut~~ — **done.** A real cut
  succeeded after the second native patch above. Both native patches and
  both Java-level gates are confirmed working end-to-end on the physical
  machine.
- The on-screen "Saldo" number will show whatever's left in
  `SharedPreferences` (starts at `0` on a fresh install) and may go negative
  over time — purely cosmetic, doesn't block cutting anymore, but could be
  patched to show a fixed "∞"/"Ilimitado" string later if wanted.
- Vendor branding elsewhere in the UI (About screen, any "UPUS"/"skycut"
  logos or text in other activities/layouts) was not swept for — this pass
  only targeted the launcher name/icon and the two gating checks. A fuller
  rebrand pass (splash screen graphic, any settings-screen vendor text) is a
  separate, lower-priority task if wanted.
- **Before deploying to a different physical machine**, read the
  "Important — verify the two native-library patches still apply" note
  under "Deploying to other machines" above — the binary patch offsets are
  specific to this firmware build and must be re-verified (or at minimum,
  the `.so` file checksummed as identical) before trusting a fresh install
  to actually cut, since the failure mode when they don't apply is
  completely silent.
