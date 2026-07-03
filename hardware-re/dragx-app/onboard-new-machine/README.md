# onboard-new-machine

One-time setup script (`onboard.py`) for onboarding a genuinely **new**
CUTTER_E326 machine: enables WiFi ADB, deploys DragX, backs up the boot
partition, checks its format against what's already been validated, and
(if the checks pass) patches the boot partition so WiFi ADB starts
automatically on every future boot. See the module docstring at the top of
`onboard.py` for the full phase-by-phase breakdown.

For **routine re-deploys** on a machine that's already been onboarded, use
the DragX Web Deployer (`hardware-re/dragx-web-deployer/`) instead — this
script is safe to re-run (Phase 3 detects "already patched" and no-ops) but
it's more machinery than a routine deploy needs.

## Prerequisites

- **The machine must already be physically rooted** (RECOVERY pins shorted,
  USB cable connected) before running this script — see
  `hardware-re/dragx-app/boot-partition-mod/README.md` for that physical
  setup step and background on why it's needed.
- **`hardware-re/dragx-web-deployer/` must exist as a sibling directory** to
  this one. `onboard.py` does a relative `sys.path` import of its `server`
  module (`_DEPLOYER_DIR = ../../dragx-web-deployer`) to reuse the deploy
  logic. If that folder is ever moved or renamed, the import fails
  immediately at startup, before any phase runs.
- **`web_deployer.ADB_PATH`** (defined in `hardware-re/dragx-web-deployer/server.py`)
  is currently hardcoded to `C:\Users\Dvilh\platform-tools\adb.exe` — a
  path specific to the workstation this was built on. On a different
  machine, or if `platform-tools` moves, any step that shells out via
  `ADB_PATH` directly (the `pull`/`push` calls in `onboard.py`) will fail
  with a bare `FileNotFoundError` traceback rather than one of this
  project's usual clear, actionable error messages. Update `ADB_PATH` in
  `server.py` first if running on a new workstation.

## Usage

```
python onboard.py
```

Assumes exactly one device is reachable via `adb devices`, connected over
USB (same single-device assumption as `hardware-re/dragx-web-deployer/server.py`).

## Fleet panel check-in (optional)

At the end of a successful run, `onboard.py` makes a best-effort call to
register the machine with the Fleet Control Panel
(`hardware-re/fleet-panel/`, live at
https://dragx-fleet-panel.onrender.com) so it shows up on the dashboard
automatically. This is controlled by two environment variables:

```bash
export PANEL_URL="https://dragx-fleet-panel.onrender.com"
export PANEL_API_KEY="<same value as the panel's CHECKIN_API_KEY>"
```

If either is unset, the check-in is silently skipped (printed as a
one-line `AVISO`, not a failure) — the rest of `onboard.py` doesn't depend
on the panel in any way. The call also uses a 60-second timeout (longer
than a typical request) because the panel is hosted on Render's free
tier, which sleeps after ~15 minutes of inactivity and can take 30-50s to
wake up; since `onboard.py` runs are infrequent, the panel is often asleep
when this call happens.
