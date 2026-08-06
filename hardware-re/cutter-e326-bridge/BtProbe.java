import java.lang.reflect.Method;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.UUID;

public class BtProbe {
    static final String MAC = "00:16:A6:01:75:2B";
    static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

    public static void main(String[] args) throws Exception {
        Class<?> adapterClass = Class.forName("android.bluetooth.BluetoothAdapter");
        Method getDefaultAdapter = adapterClass.getMethod("getDefaultAdapter");
        Object adapter = getDefaultAdapter.invoke(null);
        System.out.println("adapter: " + adapter);

        Method getRemoteDevice = adapterClass.getMethod("getRemoteDevice", String.class);
        Object device = getRemoteDevice.invoke(adapter, MAC);
        System.out.println("device: " + device);

        Class<?> deviceClass = Class.forName("android.bluetooth.BluetoothDevice");
        Method createSocket = deviceClass.getMethod("createRfcommSocketToServiceRecord", UUID.class);
        Object socket = createSocket.invoke(device, SPP_UUID);
        System.out.println("socket created: " + socket);

        Class<?> socketClass = Class.forName("android.bluetooth.BluetoothSocket");

        // cancel discovery first (recommended before connecting)
        try {
            Method cancelDiscovery = adapterClass.getMethod("cancelDiscovery");
            cancelDiscovery.invoke(adapter);
        } catch (Throwable t) {
            System.out.println("cancelDiscovery failed (continuing): " + t);
        }

        System.out.println("connecting...");
        try {
            Method connect = socketClass.getMethod("connect");
            connect.invoke(socket);
            System.out.println("connected!");
        } catch (Throwable t) {
            System.out.println("connect() failed:");
            t.printStackTrace(System.out);
            return;
        }

        Method getInputStream = socketClass.getMethod("getInputStream");
        Method getOutputStream = socketClass.getMethod("getOutputStream");
        InputStream in = (InputStream) getInputStream.invoke(socket);
        OutputStream out = (OutputStream) getOutputStream.invoke(socket);

        // Reader thread: print anything received
        final InputStream fin = in;
        Thread reader = new Thread(new Runnable() {
            public void run() {
                byte[] buf = new byte[4096];
                try {
                    while (true) {
                        int n = fin.read(buf);
                        if (n < 0) {
                            System.out.println("[reader] stream closed");
                            break;
                        }
                        String s = new String(buf, 0, n, "ISO-8859-1");
                        System.out.println("[recv " + n + " bytes] " + s);
                        StringBuilder hex = new StringBuilder();
                        for (int i = 0; i < n; i++) hex.append(String.format("%02x ", buf[i]));
                        System.out.println("[recv hex] " + hex);
                    }
                } catch (Throwable t) {
                    System.out.println("[reader] error: " + t);
                }
            }
        });
        reader.setDaemon(true);
        reader.start();

        // Just listen passively for a while first, in case the device sends something unprompted
        System.out.println("listening passively for 5s...");
        Thread.sleep(5000);

        // Try sending the known status-query command from the RCMD protocol
        String probe = "BD:10;";
        System.out.println("sending probe: " + probe);
        out.write(probe.getBytes("ISO-8859-1"));
        out.flush();

        Thread.sleep(5000);
        System.out.println("done, closing");
        try { socket.getClass().getMethod("close").invoke(socket); } catch (Throwable t) {}
    }
}
