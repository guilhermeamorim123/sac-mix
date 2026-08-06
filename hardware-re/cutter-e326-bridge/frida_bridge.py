"""
Handshake bridge for the CUTTER_E326 / rk3126c film cutter.

Attaches Frida to the already-running cn.upus.app.upprinting process and
exposes JniUtils.getHandshake(nonce) over a local TCP socket, so any future
RCMD protocol client can query it without needing to understand the RSA
handshake itself.

Requires: frida-server running on the device, matching the pinned client
version below (see hardware-re/cutter-e326-bridge/README.md).

Protocol (same as the original app_process-based Bridge.java): connect to
127.0.0.1:8654, send one line with a decimal nonce, get back one line with
the hex-encoded response bytes (or "ERROR").
"""
import socket
import sys

import frida

PORT = 8654
PACKAGE = "cn.upus.app.upprinting"


def find_target_pid(device):
    for p in device.enumerate_processes():
        try:
            # ps shows a custom process label ("Cutting"); match by identity
            # via frida's own process name only works if it reports the
            # package too, so fall back to name match on common labels.
            if p.name == PACKAGE or p.name == "Cutting":
                return p.pid
        except Exception:
            continue
    return None


def main():
    device = frida.get_usb_device(timeout=5)
    pid = find_target_pid(device)
    if pid is None:
        print("target process not running; launch it first (e.g. "
              "'adb shell monkey -p {} -c android.intent.category.LAUNCHER 1')".format(PACKAGE))
        sys.exit(1)

    print("attaching to pid", pid)
    session = device.attach(pid)
    with open("agent.js") as f:
        src = f.read()
    script = session.create_script(src)
    script.load()
    api = script.exports_sync
    print("attached and RPC ready")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", PORT))
    server.listen(5)
    print("listening on 127.0.0.1:{}".format(PORT))

    try:
        while True:
            conn, _ = server.accept()
            try:
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = conn.recv(256)
                    if not chunk:
                        break
                    buf += chunk
                nonce_str = buf.decode("ascii", "ignore").strip()
                print("recv nonce=" + nonce_str)
                try:
                    hex_result = api.gethandshake(nonce_str)
                    print("send hex=" + hex_result)
                    conn.sendall((hex_result + "\n").encode("ascii"))
                except Exception as e:
                    print("getHandshake failed:", e)
                    conn.sendall(b"ERROR\n")
            finally:
                conn.close()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        session.detach()


if __name__ == "__main__":
    main()
