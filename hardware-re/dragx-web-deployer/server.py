"""
DragX Web Deployer -- local HTTP server that installs DragX-signed.apk onto
a CUTTER_E326 machine over WiFi ADB and verifies both native-library patches.

Run: python server.py
Then open http://<this-pc-ip>:8000/ from a browser on the same WiFi network
(including an iPhone's Safari).
"""
import os
import subprocess

ADB_PATH = r"C:\Users\Dvilh\platform-tools\adb.exe"
APK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DragX-signed.apk")
TARGET_PACKAGE = "cn.upus.app.upprinting"
NATIVE_LIB_RELATIVE_PATH = "lib/arm/libnewcutjni.so"
PORT = 8000

PATCHES = [
    {
        "name": "JNI_OnLoad crash bypass",
        "offset": 0x160ee,
        "expected": bytes.fromhex("00bf"),
    },
    {
        "name": "getHandshake() certificate-check bypass",
        "offset": 0x128d4,
        "expected": bytes.fromhex("002000bf"),
    },
]


def run_adb(args):
    """Run the local adb with the given args. Returns (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [ADB_PATH] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def read_remote_bytes(lib_path, offset, count):
    """Reads `count` bytes at `offset` from `lib_path` on the connected device.
    Returns (bytes_or_None, stdout, stderr)."""
    remote_command = f"dd if={lib_path} bs=1 skip={offset} count={count} 2>/dev/null | od -An -tx1"
    exit_code, stdout, stderr = run_adb(["shell", remote_command])
    hex_tokens = stdout.split()
    if len(hex_tokens) != count:
        return None, stdout, stderr
    try:
        return bytes(int(tok, 16) for tok in hex_tokens), stdout, stderr
    except ValueError:
        return None, stdout, stderr


def deploy(ip_port):
    """Runs the full deploy flow. Returns {"overall_success": bool, "steps": [...]}."""
    steps = []

    exit_code, stdout, stderr = run_adb(["connect", ip_port])
    if not parse_connect_result(stdout):
        steps.append({"status": "failure", "message": f"Não foi possível conectar em {ip_port}: {stdout}{stderr}"})
        return {"overall_success": False, "steps": steps}
    steps.append({"status": "success", "message": f"Conectado a {ip_port}"})

    exit_code, stdout, stderr = run_adb(["install", "-r", APK_PATH])
    if not parse_install_result(stdout):
        steps.append({"status": "failure", "message": f"Falha ao instalar: {stdout}{stderr}"})
        return {"overall_success": False, "steps": steps}
    steps.append({"status": "success", "message": "DragX instalado"})

    run_adb(["shell", "am", "force-stop", TARGET_PACKAGE])
    steps.append({"status": "success", "message": "Processo antigo finalizado"})

    exit_code, stdout, stderr = run_adb(["shell", "pm", "path", TARGET_PACKAGE])
    package_dir = parse_package_dir(stdout)
    if package_dir is None:
        steps.append({"status": "failure", "message": f"Não achei o caminho do pacote instalado: {stdout}{stderr}"})
        return {"overall_success": False, "steps": steps}

    lib_path = f"{package_dir}/{NATIVE_LIB_RELATIVE_PATH}"
    all_patches_ok = True
    # Never break/return early here -- every patch must be checked even
    # after one fails, or a partially-patched device could be misreported
    # as fully working (the exact historical bug this tool exists to catch).
    for patch in PATCHES:
        actual_bytes, dd_stdout, dd_stderr = read_remote_bytes(lib_path, patch["offset"], len(patch["expected"]))
        if actual_bytes is None:
            steps.append({
                "status": "failure",
                "message": f"Não consegui ler bytes de {lib_path} no offset {patch['offset']} para checar '{patch['name']}': {dd_stdout}{dd_stderr}",
            })
            all_patches_ok = False
            continue
        passed, expected_hex, actual_hex = verify_patch(patch, actual_bytes)
        if passed:
            steps.append({"status": "success", "message": f"{patch['name']}: OK"})
        else:
            steps.append({
                "status": "failure",
                "message": f"{patch['name']}: FALHOU (esperado {expected_hex}, encontrado {actual_hex})",
            })
            all_patches_ok = False

    return {"overall_success": all_patches_ok, "steps": steps}


def parse_connect_result(stdout):
    """'adb connect' prints 'connected to <ip>:<port>' on success, and
    'already connected to <ip>:<port>' if already open -- both contain
    'connected to' as a substring."""
    return "connected to" in stdout


def parse_install_result(stdout):
    """'adb install' prints a final line 'Success' on success."""
    return any(line.strip() == "Success" for line in stdout.strip().splitlines())


def parse_package_dir(pm_path_output):
    """'adb shell pm path <pkg>' prints one line:
    'package:/data/app/<pkg>-N/base.apk'"""
    for line in pm_path_output.strip().splitlines():
        if line.startswith("package:"):
            apk_path = line[len("package:"):].strip()
            last_slash = apk_path.rfind("/")
            if last_slash <= 0:
                return None
            return apk_path[:last_slash]
    return None


def verify_patch(patch, actual_bytes):
    """Returns (passed: bool, expected_hex: str, actual_hex: str)."""
    passed = actual_bytes == patch["expected"]
    expected_hex = patch["expected"].hex(" ")
    actual_hex = actual_bytes.hex(" ")
    return passed, expected_hex, actual_hex
