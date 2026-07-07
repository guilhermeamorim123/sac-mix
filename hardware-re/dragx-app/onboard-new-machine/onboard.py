"""
onboard.py -- one-time setup for a genuinely new CUTTER_E326 machine.

Run this ONCE per new machine, immediately after the physical root step
(RECOVERY pins shorted, USB cable connected). It:
  1. Enables WiFi ADB and installs+verifies DragX (reusing the same logic
     as the routine DragX Web Deployer). If the pre-installed system
     Upprinting conflicts with DragX-signed.apk (INSTALL_FAILED_VERSION_
     DOWNGRADE / INSTALL_FAILED_UPDATE_INCOMPATIBLE -- common on a
     never-touched machine), this is now detected and fixed automatically:
     replace the /system/app baseline, reboot, clear any leftover /data/app
     update layer, and retry the install. No engineer needs to run manual
     ADB commands for this anymore.
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
IMPORTANT: keep the USB cable connected for the ENTIRE run, not just at the
start. The version-conflict recovery (see above) may need to reboot the
machine partway through, and WiFi ADB isn't persistent until Phase 3 runs
later in this same script -- without the USB cable still connected, there
would be no way to reconnect automatically after that reboot.
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


def get_usb_serial():
    """Returns the ADB serial of a device connected via USB (adb devices
    shows a bare serial like '6S9OZFRLDN', never an ip:port pair), or None
    if none is found. If more than one USB device is present, the first
    one wins -- this script is designed for one machine at a time."""
    exit_code, stdout, stderr = run_adb(["devices"])
    for line in stdout.strip().splitlines()[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue
        serial, status = line.split("\t", 1)
        if status.strip() == "device" and ":" not in serial:
            return serial
    return None


def _wait_until_responsive(ip_port, timeout_seconds=20, poll_interval=1):
    """Polls the device at ip_port (reconnecting via `adb connect` on each
    attempt, since a TCP transport's socket can drop entirely, not just go
    briefly unresponsive) until a trivial shell command succeeds, or times
    out. Returns True if the device responded within timeout_seconds."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        run_adb(["connect", ip_port])
        exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "echo", "ok"])
        if stdout.strip() == "ok":
            return True
        time.sleep(poll_interval)
    return False


def wait_for_boot(serial, timeout_seconds=600, poll_interval=5):
    """Polls `getprop sys.boot_completed` via the given adb serial until it
    reads "1", or times out. This hardware is known to take several minutes
    to finish package-manager re-optimization after a /system/app change --
    see hardware-re/dragx-app/README.md's "Android is starting..." note.
    Returns True if boot completed within timeout_seconds."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        exit_code, stdout, stderr = run_adb(["-s", serial, "shell", "getprop", "sys.boot_completed"])
        if stdout.strip() == "1":
            return True
        time.sleep(poll_interval)
    return False


def _install_failure_is_version_conflict(report):
    """True if deploy()'s failure was specifically the recurring
    INSTALL_FAILED_VERSION_DOWNGRADE / INSTALL_FAILED_UPDATE_INCOMPATIBLE
    conflict (pre-installed system Upprinting newer or differently-signed
    than DragX-signed.apk) -- as opposed to some other unrelated failure
    (network, missing file, etc.) that a reboot-and-retry wouldn't fix."""
    for step in report["steps"]:
        if step["status"] == "failure" and (
            "VERSION_DOWNGRADE" in step["message"] or "UPDATE_INCOMPATIBLE" in step["message"]
        ):
            return True
    return False


SYSTEM_APK_PATH = "/system/app/Upprinting/Upprinting.apk"


def recover_from_version_conflict(usb_serial, ip_port):
    """Handles the recurring version/signature conflict seen when a
    machine's pre-installed system Upprinting is newer or differently
    signed than DragX-signed.apk -- the exact manual procedure validated by
    hand on real machines, automated here so an employee doesn't need an
    engineer on the line for it:
      1. Root + remount /system, back up (if present) and replace the
         /system/app baseline APK with our own signed build.
      2. Reboot -- unavoidable, there's no rescan-without-reboot path on
         this old Android version for the package manager to adopt the new
         baseline.
      3. WiFi ADB isn't persistent until Phase 3 runs later in this same
         script, so the reboot drops the WiFi connection. Re-establish it
         over the USB cable -- which is why the cable must stay physically
         connected for the whole run, not just at the start.
      4. If a newer /data/app "update" layer is still shadowing the now-
         matching system baseline, uninstall it so the system version
         (ours) becomes active again.
    Returns (ok: bool, message: str)."""
    print("Detectei conflito de versão/assinatura -- tentando corrigir automaticamente...")

    if usb_serial is None:
        return False, (
            "Esse conflito precisa reiniciar a máquina pra corrigir, mas não "
            "detectei nenhum cabo USB conectado. Conecte o cabo USB (ele precisa "
            "ficar conectado durante todo o processo) e rode o script de novo."
        )

    run_adb(["-s", ip_port, "root"])
    time.sleep(2)
    exit_code, stdout, stderr = run_adb(["-s", ip_port, "remount"])
    if "succeeded" not in stdout.lower() and "already" not in stdout.lower():
        return False, f"Falha ao remontar /system: {stdout}{stderr}"

    run_adb(["-s", ip_port, "shell", "am", "force-stop", web_deployer.TARGET_PACKAGE])

    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "ls", SYSTEM_APK_PATH])
    combined = (stdout + stderr).lower()
    system_apk_exists = "no such file" not in combined

    if system_apk_exists:
        local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
        os.makedirs(local_dir, exist_ok=True)
        serial = get_device_serial(ip_port)
        backup_path = os.path.join(local_dir, f"system_apk_backup_{serial}.apk")
        pull_result = subprocess.run(
            [web_deployer.ADB_PATH, "-s", ip_port, "pull", SYSTEM_APK_PATH, backup_path],
            capture_output=True, text=True,
        )
        if pull_result.returncode == 0:
            print(f"Backup do app original do sistema salvo em {backup_path}")
        run_adb(["-s", ip_port, "shell", "rm", SYSTEM_APK_PATH])
    else:
        print("Arquivo original do sistema já não existe (ok, seguindo em frente).")

    push_result = subprocess.run(
        [web_deployer.ADB_PATH, "-s", ip_port, "push", web_deployer.APK_PATH, SYSTEM_APK_PATH],
        capture_output=True, text=True,
    )
    if push_result.returncode != 0:
        return False, f"Falha ao enviar o DragX para o caminho de sistema: {push_result.stderr}"
    run_adb(["-s", ip_port, "shell", "chmod", "644", SYSTEM_APK_PATH])

    print("Reiniciando a máquina para o sistema reconhecer a nova versão como padrão...")
    run_adb(["-s", ip_port, "reboot"])

    print("Aguardando o boot (pode levar vários minutos nesse hardware)...")
    if not wait_for_boot(usb_serial, timeout_seconds=600):
        return False, (
            "A máquina não terminou de reiniciar em 10 minutos. Veja a tela dela; "
            "se estiver travada em 'Android is starting...', desligue e ligue na "
            "tomada e rode este script de novo (o cabo USB precisa continuar "
            "conectado)."
        )

    run_adb(["-s", usb_serial, "tcpip", "5555"])
    time.sleep(2)
    run_adb(["connect", ip_port])
    time.sleep(2)

    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "pm", "path", web_deployer.TARGET_PACKAGE])
    package_dir = web_deployer.parse_package_dir(stdout)
    if package_dir and package_dir.startswith("/data/app"):
        print("Ainda existe uma versão antiga sobreposta em /data/app -- removendo...")
        run_adb(["-s", ip_port, "shell", "pm", "uninstall", web_deployer.TARGET_PACKAGE])

    return True, "Correção aplicada -- tentando instalar de novo"


def phase1_setup_wifi_and_deploy(usb_serial):
    print("=== FASE 1: WiFi ADB + Deploy do DragX ===")

    exit_code, stdout, stderr = run_adb(["-s", usb_serial, "tcpip", "5555"])
    print(f"adb tcpip 5555: {stdout}{stderr}".strip())
    time.sleep(2)

    ip = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        exit_code, stdout, stderr = run_adb(["-s", usb_serial, "shell", "ip", "addr", "show", "wlan0"])
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

    if not report["overall_success"] and _install_failure_is_version_conflict(report):
        ok, message = recover_from_version_conflict(usb_serial, ip_port)
        print(f"{'OK  ' if ok else 'ERRO'} - {message}")
        if ok:
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
    # instantly once any ADB connection was already established") -- but
    # over a WiFi/TCP transport specifically, `adb root` restarting adbd
    # also drops the TCP socket, and a fixed sleep(2) isn't always long
    # enough for it to come back (confirmed once as "device offline" on a
    # real onboarding run). Poll instead of guessing a fixed delay.
    exit_code, stdout, stderr = run_adb(["-s", ip_port, "root"])
    print(f"adb root: {stdout}{stderr}".strip())
    if not _wait_until_responsive(ip_port, timeout_seconds=20):
        return None, "O dispositivo não respondeu depois de 'adb root' (ficou offline). Tente rodar de novo."

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
    # 60s (not _post_json's default 10s): the panel is hosted on Render's
    # free tier, which sleeps after ~15 minutes of inactivity and can take
    # 30-50s to wake on the next request. onboard.py runs are infrequent
    # (once per new machine), so the panel will very plausibly be asleep
    # when this call happens -- a 10s timeout would spuriously report this
    # best-effort check-in as failed even though the panel would have
    # succeeded given more time. Scoped to just this call, not a change to
    # _post_json's default, since nothing else in this script needs it.
    try:
        status = _post_json(url, payload, headers, timeout=60)
    except Exception as e:
        return False, f"não consegui contatar o painel: {e}"
    if status == 200:
        return True, "registrado no painel com sucesso"
    return False, f"painel respondeu com status {status}"


def get_device_serial(ip_port):
    """Returns the device's real ADB serial number (e.g. '6S9OZFRLDN'),
    not the ip:port transport address -- this is the stable identifier
    the fleet panel keys machine records on. Uses `getprop ro.serialno`
    rather than `adb get-serialno`, because for a device connected over
    TCP/IP (which is always the case at this point in onboard.py's flow),
    `adb get-serialno` returns the ip:port transport address itself, not
    the underlying hardware serial -- confirmed by testing both against a
    real device."""
    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "getprop", "ro.serialno"])
    return stdout.strip()


def _parse_version_name(dumpsys_output):
    """Parses 'adb shell dumpsys package <pkg>' output and returns the
    versionName value (e.g. 'V7.0.3.005'), or None if no versionName= line
    is present. If more than one versionName= line is present, the first
    match wins -- this is the current, intentional behavior."""
    for line in dumpsys_output.splitlines():
        line = line.strip()
        if line.startswith("versionName="):
            return line[len("versionName="):]
    return None


def get_dragx_version(ip_port):
    """Returns the installed DragX app's versionName (e.g. 'V7.0.3.005'),
    or None if it couldn't be determined."""
    exit_code, stdout, stderr = run_adb([
        "-s", ip_port, "shell", "dumpsys", "package", web_deployer.TARGET_PACKAGE,
    ])
    return _parse_version_name(stdout)


def main():
    usb_serial = get_usb_serial()
    if usb_serial is None:
        print("ERRO: não detectei nenhum dispositivo conectado por USB.")
        print("Conecte o cabo USB e rode este script de novo -- e deixe o cabo")
        print("conectado durante todo o processo, não só no começo (pode ser")
        print("necessário reiniciar a máquina no meio do processo, e sem o cabo")
        print("não tem como reconectar sozinho depois de um reboot).")
        sys.exit(1)
    print(f"Dispositivo USB detectado: {usb_serial}")

    ip_port = phase1_setup_wifi_and_deploy(usb_serial)
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
