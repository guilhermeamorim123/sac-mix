import java.lang.reflect.Method;
import java.io.InputStream;
import java.io.OutputStream;

public class BtProbe3 {
    static final String MAC = "00:16:A6:01:75:2B";

    public static void main(String[] args) throws Exception {
        Class<?> adapterClass = Class.forName("android.bluetooth.BluetoothAdapter");
        Method getDefaultAdapter = adapterClass.getMethod("getDefaultAdapter");
        Object adapter = getDefaultAdapter.invoke(null);

        Method getRemoteDevice = adapterClass.getMethod("getRemoteDevice", String.class);
        Object device = getRemoteDevice.invoke(adapter, MAC);

        Class<?> deviceClass = Class.forName("android.bluetooth.BluetoothDevice");
        try {
            Method cancelDiscovery = adapterClass.getMethod("cancelDiscovery");
            cancelDiscovery.invoke(adapter);
        } catch (Throwable t) {}

        // Hidden API: createRfcommSocket(int channel) - bypasses SDP entirely
        Method createSocket = deviceClass.getMethod("createRfcommSocket", int.class);

        for (int channel = 1; channel <= 5; channel++) {
            System.out.println("=== trying channel " + channel + " ===");
            Object socket = createSocket.invoke(device, channel);
            Class<?> socketClass = Class.forName("android.bluetooth.BluetoothSocket");
            Method connect = socketClass.getMethod("connect");
            long t0 = System.currentTimeMillis();
            try {
                connect.invoke(socket);
                System.out.println("channel " + channel + ": CONNECTED at +" + (System.currentTimeMillis()-t0) + "ms");

                Method getInputStream = socketClass.getMethod("getInputStream");
                Method getOutputStream = socketClass.getMethod("getOutputStream");
                InputStream in = (InputStream) getInputStream.invoke(socket);
                OutputStream out = (OutputStream) getOutputStream.invoke(socket);

                // send probe and read response
                out.write("BD:10;".getBytes("ISO-8859-1"));
                out.flush();
                System.out.println("sent probe, reading for 3s...");

                long deadline = System.currentTimeMillis() + 3000;
                byte[] buf = new byte[4096];
                while (System.currentTimeMillis() < deadline) {
                    if (in.available() > 0) {
                        int n = in.read(buf);
                        String s = new String(buf, 0, n, "ISO-8859-1");
                        System.out.println("[recv " + n + "] " + s);
                    }
                    Thread.sleep(100);
                }
                try { socketClass.getMethod("close").invoke(socket); } catch (Throwable t) {}
                System.out.println("--- channel " + channel + " done, stopping search (found working channel) ---");
                return;
            } catch (Throwable t) {
                System.out.println("channel " + channel + ": failed at +" + (System.currentTimeMillis()-t0) + "ms: " + t.getCause());
                try { socketClass.getMethod("close").invoke(socket); } catch (Throwable t2) {}
            }
        }
        System.out.println("no channel 1-5 worked");
    }
}
