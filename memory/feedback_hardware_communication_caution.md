---
name: feedback-hardware-communication-caution
description: Never send raw/undocumented commands directly to physical hardware interfaces (serial ports, etc.) outside the app's own code path — real machines can end up in a bad state
metadata:
  type: feedback
---

Never write raw bytes directly to a hardware communication interface (serial port device node, etc.) to "quickly test" a protocol command, even with root access and even when the goal (e.g. reading an LED's current behavior) seems harmless.

**Why:** During [[project-dragx-fleet]] work (2026-07-21), sent a raw test command (`echo -ne 'BD:100,106;' > /dev/ttyS1`) directly to a film-cutting machine's serial port, bypassing the app's own connection-init/handshake sequence. The machine's cutter-control board ended up in a confused "reconectando" (reconnecting) state, requiring a full physical power cycle of the machine to recover. No data was lost, but it was a real, unplanned outage of a customer-facing device caused directly by an unnecessarily risky diagnostic shortcut.

**How to apply:** When investigating any hardware protocol behavior (serial ports, GPIO, custom board commands, etc.) on a REAL, potentially-in-use device:
- Always trigger commands through the app's own existing code path (a real button in the UI, a documented API call) rather than writing raw bytes directly to a device node — the app's init/handshake sequence often matters and bypassing it can leave the hardware in an undefined state.
- If no safe in-app trigger exists, treat this as a "needs more preparation" task (get vendor documentation, test on a non-production unit, or ask the owner directly) rather than experimenting live.
- This caution generalizes beyond this specific project to any embedded/hardware-adjacent work: local/software-only experiments are safe to iterate on quickly; physical-hardware experiments deserve the same caution as a production database migration.
