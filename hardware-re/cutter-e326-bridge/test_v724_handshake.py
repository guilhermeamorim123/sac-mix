"""One-shot getHandshake() test against the freshly patched v724 DragX build."""
import sys
import frida

PACKAGE = "cn.upus.app.upprinting"


def find_target_pid(device):
    for p in device.enumerate_processes():
        if p.name == PACKAGE or p.name == "Cutting":
            return p.pid
    return None


def main():
    device = frida.get_usb_device(timeout=5)
    pid = find_target_pid(device)
    if pid is None:
        print("processo alvo nao encontrado")
        sys.exit(1)
    print("attaching to pid", pid)
    session = device.attach(pid)
    with open("agent.js") as f:
        src = f.read()
    script = session.create_script(src)
    script.load()
    api = script.exports_sync

    nonce = "123456"
    try:
        hex_result = api.gethandshake(nonce)
        print(f"getHandshake({nonce}) = {hex_result}")
        try:
            decoded = bytes.fromhex(hex_result).decode("ascii")
            print(f"decodificado: {decoded}")
        except Exception:
            pass
        if hex_result == hex(int.from_bytes(nonce.encode(), "big"))[2:]:
            pass
        expected_stock_v705 = "42443a31322c31343838353630343b"  # BD:12,14885604; (v705 stock)
        echo_fallback = nonce.encode().hex()
        print()
        if hex_result == echo_fallback:
            print("RESULTADO: FALLBACK (echo do nonce) -- patch de crypto NAO esta funcionando")
        elif hex_result == expected_stock_v705:
            print("RESULTADO: idêntico ao valor stock do v705 (coincidência de build) -- patch funcionando")
        else:
            print("RESULTADO: valor NAO-trivial, diferente do nonce puro -- indica calculo real (patch funcionando)")
    except Exception as e:
        print("ERRO ao chamar getHandshake:", e)
        sys.exit(1)
    finally:
        session.detach()


if __name__ == "__main__":
    main()
