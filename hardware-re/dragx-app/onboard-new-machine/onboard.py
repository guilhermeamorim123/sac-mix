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
import json
import os
import sys
import time
import urllib.request

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
        return None, f"Não consegui ler mtdparts= de /proc/cmdline -- layout de partição desconhecido. Saída: {stdout}{stderr}"

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


import hashlib


def phase3_patch_and_write(ip_port, check_result):
    print("=== FASE 3: Aplicando o patch de boot ===")

    entries = check_result["entries"]
    patched_entries, already_patched = boot_patch.patch_init_usb_rc(list(entries))

    if already_patched:
        print("init.usb.rc já contém o gatilho de WiFi ADB -- essa máquina já foi configurada antes.")
        print("Nada a fazer. FASE 3: OK (sem alterações)\n")
        return True

    new_ramdisk = boot_patch.rebuild_cpio(patched_entries)
    max_compressed_size = check_result["partition_size"] - 8 - len(check_result["kernel_tail"])

    try:
        compressed = boot_patch.compress_ramdisk_to_fit(new_ramdisk, max_compressed_size)
    except ValueError as e:
        print(f"ERRO: {e}")
        print("Não escrevi nada. A máquina continua exatamente como estava.")
        return False

    try:
        new_image = boot_patch.reassemble_boot_image(
            compressed, check_result["kernel_tail"], check_result["partition_size"]
        )
    except ValueError as e:
        print(f"ERRO: {e}")
        print("Não escrevi nada. A máquina continua exatamente como estava.")
        return False

    ok, message = boot_patch.verify_roundtrip(
        new_image, expected_kernel_tail=check_result["kernel_tail"], must_contain_trigger=True
    )
    if not ok:
        print(f"ERRO na verificação antes de gravar: {message}")
        print("Não escrevi nada. A máquina continua exatamente como estava.")
        return False
    print(f"Verificação antes de gravar: {message}")

    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
    safe_ip = ip_port.replace(":", "_")
    local_modified_path = os.path.join(local_dir, f"boot_modified_{safe_ip}.img")
    open(local_modified_path, "wb").write(new_image)

    remote_modified_path = "/data/onboard_boot_modified.img"
    push_result = subprocess.run(
        [web_deployer.ADB_PATH, "-s", ip_port, "push", local_modified_path, remote_modified_path],
        capture_output=True, text=True,
    )
    if push_result.returncode != 0:
        print(f"ERRO ao enviar a imagem modificada: {push_result.stderr}")
        return False

    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "md5sum", remote_modified_path])
    pushed_md5 = stdout.strip().split()[0] if stdout.strip() else None
    expected_md5 = hashlib.md5(new_image).hexdigest()
    if pushed_md5 != expected_md5:
        print(f"ERRO: md5 não bateu após o envio ({pushed_md5} != {expected_md5}). Não vou gravar na partição.")
        return False
    print("Transferência verificada por md5.")

    local_backup_path = os.path.join(local_dir, f"boot_backup_{safe_ip}.img")

    block_count = check_result["partition_size"] // 4096
    exit_code, stdout, stderr = run_adb([
        "-s", ip_port, "shell",
        f"dd if={remote_modified_path} of={check_result['device_path']} bs=4096 count={block_count}",
    ])
    if "records out" not in stdout and "records out" not in stderr:
        print(f"ERRO CRÍTICO ao gravar na partição: {stdout}{stderr}")
        print("A gravação pode ter ficado corrompida/incompleta. NÃO reinicie a máquina -- restaure o backup primeiro:")
        print(f"  adb push {local_backup_path} /data/restore.img")
        print(f"  adb shell dd if=/data/restore.img of={check_result['device_path']} bs=4096")
        return False
    print("Gravado na partição de boot.")

    exit_code, stdout, stderr = run_adb([
        "-s", ip_port, "shell",
        f"dd if={check_result['device_path']} bs=4096 count={block_count} | md5sum",
    ])
    onpartition_md5 = stdout.strip().split()[0] if stdout.strip() else None
    if onpartition_md5 != expected_md5:
        print(f"ERRO CRÍTICO: md5 da partição após a gravação não bateu ({onpartition_md5} != {expected_md5}).")
        print("A gravação pode ter ficado corrompida. NÃO reinicie a máquina -- restaure o backup primeiro:")
        print(f"  adb push {local_backup_path} /data/restore.img")
        print(f"  adb shell dd if=/data/restore.img of={check_result['device_path']} bs=4096")
        return False
    print("Verificação pós-gravação: md5 da partição bate com o esperado.")

    print("FASE 3: OK\n")
    return True


def _post_json(url, payload_dict, headers, timeout=10):
    """Thin wrapper around urlopen, extracted into its own function so
    tests can monkeypatch it (same pattern as web_deployer.run_adb being
    monkeypatched in hardware-re/dragx-web-deployer/selfcheck.py) instead
    of needing a real network connection."""
    data = json.dumps(payload_dict).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def checkin_with_panel(serial, dragx_version):
    """Best-effort registration with the fleet panel. Never raises --
    always returns (ok: bool, message: str), so a panel outage can never
    fail an onboarding run. Reads PANEL_URL and PANEL_API_KEY from
    environment variables; if either is unset, the integration is
    considered disabled and this returns False immediately."""
    panel_url = os.environ.get("PANEL_URL")
    api_key = os.environ.get("PANEL_API_KEY")
    if not panel_url or not api_key:
        return False, "PANEL_URL ou PANEL_API_KEY não configurados (integração com painel desativada)"

    url = f"{panel_url.rstrip('/')}/api/machines/checkin"
    headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
    payload = {"serial": serial, "dragx_version": dragx_version}
    try:
        status = _post_json(url, payload, headers)
    except Exception as e:
        return False, f"não consegui contatar o painel: {e}"
    if status == 200:
        return True, "registrado no painel com sucesso"
    return False, f"painel respondeu com status {status}"


def get_device_serial(ip_port):
    """Returns the device's real ADB serial number (e.g. '6S9OZFRLDN'),
    not the ip:port transport address -- this is the stable identifier
    the fleet panel keys machine records on."""
    exit_code, stdout, stderr = run_adb(["-s", ip_port, "get-serialno"])
    return stdout.strip()


def get_dragx_version(ip_port):
    """Returns the installed DragX app's versionName (e.g. 'V7.0.3.005'),
    or None if it couldn't be determined."""
    exit_code, stdout, stderr = run_adb([
        "-s", ip_port, "shell", "dumpsys", "package", web_deployer.TARGET_PACKAGE,
    ])
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("versionName="):
            return line[len("versionName="):]
    return None


def main():
    exit_code, stdout, stderr = run_adb(["devices"])
    print(stdout)

    ip_port = phase1_setup_wifi_and_deploy()
    check_result, error = phase2_backup_and_check(ip_port)

    if check_result is None:
        print(f"\nFASE 2 FALHOU: {error}")
        print("PARANDO AQUI. Nada foi escrito na partição de boot.")
        print("O backup, se algum foi feito com sucesso antes do erro, está em ./backups/")
        sys.exit(1)

    success = phase3_patch_and_write(ip_port, check_result)
    if not success:
        print("\nFASE 3 não completou com sucesso. Veja as mensagens acima.")
        print("O backup da partição de boot, se algum foi feito, está em ./backups/")
        sys.exit(1)

    serial = get_device_serial(ip_port)
    dragx_version = get_dragx_version(ip_port)
    panel_ok, panel_message = checkin_with_panel(serial, dragx_version)
    marker = "OK  " if panel_ok else "AVISO"
    print(f"{marker} - Painel: {panel_message}")

    print("=" * 60)
    print("PRONTO. Agora teste com um desliga-religa REAL (não adb reboot,")
    print("tira da tomada de verdade) e confirme que:")
    print(f"  1. A máquina liga normalmente")
    print(f"  2. 'adb connect {ip_port}' funciona sozinho, sem cabo USB")
    print(f"  3. O app DragX abre normalmente")
    print("Se a máquina não ligar corretamente: restaure o backup em")
    print(f"./backups/boot_backup_{ip_port.replace(':', '_')}.img via adb shell dd")
    print("(veja hardware-re/dragx-app/boot-partition-mod/README.md, seção")
    print("'If this ever needs to be undone').")
    print("=" * 60)


if __name__ == "__main__":
    main()
