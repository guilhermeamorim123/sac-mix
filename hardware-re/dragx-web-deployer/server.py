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
