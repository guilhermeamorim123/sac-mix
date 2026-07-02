"""
DragX Web Deployer -- local HTTP server that installs DragX-signed.apk onto
a CUTTER_E326 machine over WiFi ADB and verifies both native-library patches.

Run: python server.py
Then open http://<this-pc-ip>:8000/ from a browser on the same WiFi network
(including an iPhone's Safari).
"""
import os

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
