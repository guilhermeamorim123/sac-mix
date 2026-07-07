"""
DragX Web Deployer -- local HTTP server that installs DragX-signed.apk onto
a CUTTER_E326 machine over WiFi ADB and verifies both native-library patches.

Run: python server.py
Then open http://<this-pc-ip>:8000/ from a browser on the same WiFi network
(including an iPhone's Safari).
"""
import http.server
import json
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


def read_remote_bytes(ip_port, lib_path, offset, count):
    """Reads `count` bytes at `offset` from `lib_path` on the device at
    ip_port. Returns (bytes_or_None, stdout, stderr)."""
    remote_command = f"dd if={lib_path} bs=1 skip={offset} count={count} | od -An -tx1"
    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", remote_command])
    hex_tokens = stdout.split()
    if len(hex_tokens) != count:
        return None, stdout, stderr
    try:
        return bytes(int(tok, 16) for tok in hex_tokens), stdout, stderr
    except ValueError:
        return None, stdout, stderr


def deploy(ip_port):
    """Runs the full deploy flow. Returns {"overall_success": bool, "steps": [...]}.

    Every adb call after the initial `connect` is explicitly targeted at
    `ip_port` via `-s` -- this works correctly even when a USB cable is
    connected to the same device at the same time (as onboard.py now
    requires, so it can recover from a mid-run reboot without a human
    reconnecting the cable). Before this, `deploy()` relied on "exactly
    one device reachable via adb" and would fail with "more than one
    device/emulator" whenever USB and WiFi were both live -- see
    VALIDATION.md's former "Known limitation" section for the real-hardware
    case that first surfaced this."""
    steps = []

    exit_code, stdout, stderr = run_adb(["connect", ip_port])
    if not parse_connect_result(stdout):
        steps.append({"status": "failure", "message": f"Não foi possível conectar em {ip_port}: {stdout}{stderr}"})
        return {"overall_success": False, "steps": steps}
    steps.append({"status": "success", "message": f"Conectado a {ip_port}"})

    exit_code, stdout, stderr = run_adb(["-s", ip_port, "install", "-r", APK_PATH])
    if not parse_install_result(stdout):
        steps.append({"status": "failure", "message": f"Falha ao instalar: {stdout}{stderr}"})
        return {"overall_success": False, "steps": steps}
    steps.append({"status": "success", "message": "DragX instalado"})

    run_adb(["-s", ip_port, "shell", "am", "force-stop", TARGET_PACKAGE])
    steps.append({"status": "success", "message": "Processo antigo finalizado"})

    exit_code, stdout, stderr = run_adb(["-s", ip_port, "shell", "pm", "path", TARGET_PACKAGE])
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
        actual_bytes, dd_stdout, dd_stderr = read_remote_bytes(ip_port, lib_path, patch["offset"], len(patch["expected"]))
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


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class DeployerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/deploy":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)
                ip_port = data.get("ip_port", "").strip()
            except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
                self._send_json(400, {"overall_success": False, "steps": [{"status": "failure", "message": "Requisição inválida"}]})
                return
            if not ip_port:
                self._send_json(400, {"overall_success": False, "steps": [{"status": "failure", "message": "IP:porta vazio"}]})
                return
            report = deploy(ip_port)
            self._send_json(200, report)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, path, content_type):
        with open(path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Keep console output focused on deploy activity, not every request.
        pass


def main():
    if not os.path.exists(ADB_PATH):
        print(f"ERRO: adb não encontrado em {ADB_PATH}")
        return
    if not os.path.exists(APK_PATH):
        print(f"ERRO: DragX-signed.apk não encontrado em {APK_PATH}")
        return

    # Binds on all interfaces with no authentication, by design -- this is a
    # single-operator tool meant only for a trusted home/small-office WiFi
    # network. Anyone on that same network can trigger a deploy against any
    # ip:port they choose. Do not expose this port beyond a trusted LAN.
    server_instance = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), DeployerHandler)
    print("DragX Web Deployer rodando.")
    print(f"Abra no navegador: http://localhost:{PORT}/")
    print(f"Ou de outro aparelho na mesma rede WiFi (ex: iPhone): http://<IP deste PC>:{PORT}/")
    server_instance.serve_forever()


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


if __name__ == "__main__":
    main()
