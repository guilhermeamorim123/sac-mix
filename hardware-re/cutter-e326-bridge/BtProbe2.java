import java.lang.reflect.Method;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.UUID;

public class BtProbe2 {
    static final String MAC = "00:16:A6:01:75:2B";
    static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

    public static void main(String[] args) throws Exception {
        Class<?> adapterClass = Class.forName("android.bluetooth.BluetoothAdapter");
        Method getDefaultAdapter = adapterClass.getMethod("getDefaultAdapter");
        Object adapter = getDefaultAdapter.invoke(null);

        Method getRemoteDevice = adapterClass.getMethod("getRemoteDevice", String.class);
        Object device = getRemoteDevice.invoke(adapter, MAC);

        Class<?> deviceClass = Class.forName("android.bluetooth.BluetoothDevice");
        Method createSocket = deviceClass.getMethod("createInsecureRfcommSocketToServiceRecord", UUID.class);
        Object socket = createSocket.invoke(device, SPP_UUID);

        Class<?> socketClass = Class.forName("android.bluetooth.BluetoothSocket");
        try {
            Method cancelDiscovery = adapterClass.getMethod("cancelDiscovery");
            cancelDiscovery.invoke(adapter);
        } catch (Throwable t) {}

        long t0 = System.currentTimeMillis();
        System.out.println("connecting...");
        Method connect = socketClass.getMethod("connect");
        try {
            connect.invoke(socket);
        } catch (Throwable t) {
            System.out.println("connect failed at +" + (System.currentTimeMillis()-t0) + "ms: " + t);
            if (t.getCause() != null) t.getCause().printStackTrace(System.out);
            return;
        }
        System.out.println("connected at +" + (System.currentTimeMillis()-t0) + "ms");

        Method getInputStream = socketClass.getMethod("getInputStream");
        final InputStream in = (InputStream) getInputStream.invoke(socket);

        // just try reading, no writing at all, see how long it stays open / what arrives
        byte[] buf = new byte[4096];
        try {
            while (true) {
                int n = in.read(buf);
                long t = System.currentTimeMillis() - t0;
                if (n < 0) {
                    System.out.println("[+" + t + "ms] stream closed (read=-1)");
                    break;
                }
                String s = new String(buf, 0, n, "ISO-8859-1");
                System.out.println("[+" + t + "ms recv " + n + " bytes] " + s);
                StringBuilder hex = new StringBuilder();
                for (int i = 0; i < n; i++) hex.append(String.format("%02x ", buf[i]));
                System.out.println("[hex] " + hex);
            }
        } catch (Throwable e) {
            long t = System.currentTimeMillis() - t0;
            System.out.println("[+" + t + "ms] read error: " + e);
        }
        System.out.println("done");
    }
}
