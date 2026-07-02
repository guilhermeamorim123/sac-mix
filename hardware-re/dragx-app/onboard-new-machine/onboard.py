"""
onboard.py -- one-time setup for a genuinely new CUTTER_E326 machine.

Run this ONCE per new machine, immediately after the physical root step
(RECOVERY pins shorted, USB cable connected). It:
  1. Enables WiFi ADB and installs+verifies DragX (reusing the same logic
     as the routine DragX Web Deployer).
  2. Backs up the boot partition and checks its format matches what's
     already been validated on the original machine.
  3. If the checks pass, patches the boot partition so WiFi ADB starts
     automatically on every future boot -- eliminating the need to ever
     physically touch this specific machine again.

For routine re-deploys on an already-onboarded machine, use the DragX Web
Deployer (hardware-re/dragx-web-deployer/) instead. Running this script
again against an already-onboarded machine is safe (Phase 3 detects
"already patched" and does nothing) but pointless -- there's no reason to
repeat it.

Usage: python onboard.py
Assumes exactly one device is reachable via `adb devices`, connected over
USB (same single-device assumption as hardware-re/dragx-web-deployer/server.py).
"""
import os
import sys
import time

_DEPLOYER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "dragx-web-deployer"
)
sys.path.insert(0, os.path.abspath(_DEPLOYER_DIR))
import server as web_deployer  # noqa: E402

import boot_patch  # noqa: E402


def run_adb(args):
    return web_deployer.run_adb(args)


def phase1_setup_wifi_and_deploy():
    print("=== FASE 1: WiFi ADB + Deploy do DragX ===")

    exit_code, stdout, stderr = run_adb(["tcpip", "5555"])
    print(f"adb tcpip 5555: {stdout}{stderr}".strip())
    time.sleep(2)

    ip = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        exit_code, stdout, stderr = run_adb(["shell", "ip", "addr", "show", "wlan0"])
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                ip = line.split()[1].split("/")[0]
                break
        if ip is not None:
            break
        if attempt < max_attempts:
            print(f"tentativa {attempt}/{max_attempts} falhou, tentando de novo...")
            time.sleep(2)
    if ip is None:
        print("ERRO: não consegui descobrir o IP WiFi da máquina.")
        print(f"Saída de 'ip addr show wlan0':\n{stdout}{stderr}")
        sys.exit(1)
    print(f"IP WiFi encontrado: {ip}")

    ip_port = f"{ip}:5555"
    report = web_deployer.deploy(ip_port)
    for step in report["steps"]:
        marker = "OK  " if step["status"] == "success" else "ERRO"
        print(f"{marker} - {step['message']}")

    if not report["overall_success"]:
        print("\nFASE 1 FALHOU. Parando aqui -- não vou mexer na partição de boot")
        print("sem confirmar primeiro que o DragX básico está funcionando.")
        sys.exit(1)

    print("\nFASE 1: OK\n")
    return ip_port


if __name__ == "__main__":
    ip_port = phase1_setup_wifi_and_deploy()
    print(f"(fim do teste da Fase 1 -- ip_port = {ip_port})")
