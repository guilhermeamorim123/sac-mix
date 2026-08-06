import frida, time, sys

def on_message(message, data):
    if message.get('type') == 'send':
        print(message['payload'], flush=True)
    else:
        print(message, flush=True)

device = frida.get_usb_device(timeout=5)
session = device.attach(int(sys.argv[1]))
with open(r'C:\Users\Dvilh\AppData\Local\Temp\claude\c--Users-Dvilh-OneDrive-Desktop-BIG-FRIEND-Chief-of-Staff\90e1413f-8128-4080-bca0-a557ab0a7bbc\scratchpad\hook_serial.js') as f:
    src = f.read()
script = session.create_script(src)
script.on('message', on_message)
script.load()
print("HOOKS INSTALLED - listening for 90 seconds, go press the cut button now", flush=True)
time.sleep(90)
print("done listening", flush=True)
session.detach()
