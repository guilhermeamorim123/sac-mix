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


import subprocess

BOOT_PARTITION_NAME = "boot"


def phase2_backup_and_check(ip_port):
    print("=== FASE 2: Backup e checagem de segurança ===")

    # /proc/cmdline and the raw boot block device are root:radio, mode 0640
    # -- unreadable by the default "shell" adb user. Phase 1's `adb tcpip
    # 5555` restarts adbd and drops any prior root elevation, so we need to
    # re-elevate here. This is the same step documented as safe and
    # instantaneous on this exact hardware in
    # hardware-re/dragx-app/boot-partition-mod/README.md ("adb root worked
    # instantly once any ADB connection was already established").
    exit_code, stdout, stderr = run_adb(["-s", ip_port, "root"])
    print(f"adb root: {stdout}{stderr}".strip())
    time.sleep(2)

    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "cat", "/proc/cmdline"])
    mtdparts = boot_patch.parse_mtdparts(stdout)
    if not mtdparts:
        return None, "Não consegui ler mtdparts= de /proc/cmdline -- layout de partição desconhecido."

    result = boot_patch.find_partition_device(mtdparts, BOOT_PARTITION_NAME)
    if result is None:
        return None, f"Não achei uma partição chamada '{BOOT_PARTITION_NAME}' em mtdparts."
    partition_number, partition_size = result
    device_path = f"/dev/block/mmcblk0p{partition_number}"
    print(f"Partição de boot: {device_path} ({partition_size} bytes)")

    block_count = partition_size // 4096
    remote_backup_path = "/data/onboard_boot_backup.img"
    exit_code, stdout, stderr = run_adb([
        "-s", ip_port, "shell",
        f"dd if={device_path} of={remote_backup_path} bs=4096 count={block_count}",
    ])
    if "records out" not in stdout and "records out" not in stderr:
        return None, f"Backup da partição falhou: {stdout}{stderr}"
    print("Backup bruto da partição concluído (no próprio dispositivo).")

    local_backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
    os.makedirs(local_backup_dir, exist_ok=True)
    safe_ip = ip_port.replace(":", "_")
    local_backup_path = os.path.join(local_backup_dir, f"boot_backup_{safe_ip}.img")
    pull_result = subprocess.run(
        [web_deployer.ADB_PATH, "-s", ip_port, "pull", remote_backup_path, local_backup_path],
        capture_output=True, text=True,
    )
    if pull_result.returncode != 0:
        return None, f"Falha ao copiar o backup pro PC: {pull_result.stderr}"
    print(f"Backup também copiado pro PC: {local_backup_path}")

    image_bytes = open(local_backup_path, "rb").read()
    if len(image_bytes) != partition_size:
        return None, f"Backup tem {len(image_bytes)} bytes, esperado {partition_size}."

    try:
        compressed_ramdisk, kernel_tail = boot_patch.parse_boot_image(image_bytes)
        ramdisk = boot_patch.decompress_ramdisk(compressed_ramdisk)
        entries = boot_patch.parse_cpio_entries(ramdisk)
    except ValueError as e:
        return None, f"Formato da imagem de boot não bateu com o esperado: {e}"

    init_usb_rc = boot_patch.find_entry(entries, "init.usb.rc")
    if init_usb_rc is None:
        return None, "init.usb.rc não encontrado dentro do ramdisk."

    print(f"Checagem: {len(entries)} arquivos no ramdisk, init.usb.rc presente ({init_usb_rc['filesize']} bytes).")
    print("FASE 2: checagens bateram.\n")

    return {
        "image_bytes": image_bytes,
        "compressed_ramdisk": compressed_ramdisk,
        "kernel_tail": kernel_tail,
        "entries": entries,
        "partition_size": partition_size,
        "device_path": device_path,
    }, None


if __name__ == "__main__":
    ip_port = phase1_setup_wifi_and_deploy()
    check_result, error = phase2_backup_and_check(ip_port)
    if check_result is None:
        print(f"\nFASE 2 FALHOU: {error}")
        sys.exit(1)
    print(f"(fim do teste da Fase 2 -- partição: {check_result['device_path']}, "
          f"{len(check_result['entries'])} entradas no cpio)")
