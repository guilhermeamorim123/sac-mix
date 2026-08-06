import com.cut.cutjni.JniUtils;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

public class Bridge {
    private static final int PORT = 8654;

    private static void fabricateContext() {
        try {
            Class<?> looperClass = Class.forName("android.os.Looper");
            Method prepareMainLooper = looperClass.getMethod("prepareMainLooper");
            prepareMainLooper.invoke(null);

            Class<?> activityThreadClass = Class.forName("android.app.ActivityThread");
            Method systemMain = activityThreadClass.getMethod("systemMain");
            Object activityThread = systemMain.invoke(null);
            System.out.println("ActivityThread.systemMain() ok: " + activityThread);

            Method getSystemContext = activityThreadClass.getMethod("getSystemContext");
            Object context = getSystemContext.invoke(activityThread);
            System.out.println("system context: " + context);

            Class<?> contextClass = Class.forName("android.content.Context");
            Method createPackageContext = contextClass.getMethod("createPackageContext", String.class, int.class);
            int CONTEXT_INCLUDE_CODE = 1;
            int CONTEXT_IGNORE_SECURITY = 2;
            Object pkgContext = createPackageContext.invoke(context, "cn.upus.app.upprinting", CONTEXT_INCLUDE_CODE | CONTEXT_IGNORE_SECURITY);
            System.out.println("package context: " + pkgContext);

            Method getPackageName = contextClass.getMethod("getPackageName");
            System.out.println("package context packageName: " + getPackageName.invoke(pkgContext));

            Method getClassLoader = contextClass.getMethod("getClassLoader");
            Object pkgClassLoader = getClassLoader.invoke(pkgContext);
            Thread.currentThread().setContextClassLoader((ClassLoader) pkgClassLoader);
            System.out.println("set thread context classloader to: " + pkgClassLoader);
        } catch (Throwable t) {
            System.out.println("fabricateContext failed (continuing anyway):");
            t.printStackTrace(System.out);
        }
    }

    public static void main(String[] args) throws Exception {
        fabricateContext();
        ServerSocket server = new ServerSocket(PORT, 50, InetAddress.getByName("127.0.0.1"));
        System.out.println("listening on 127.0.0.1:" + PORT);

        while (true) {
            try (Socket socket = server.accept()) {
                handle(socket);
            } catch (Throwable t) {
                System.out.println("connection error:");
                t.printStackTrace(System.out);
            }
        }
    }

    private static void handle(Socket socket) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.US_ASCII));
        OutputStream out = socket.getOutputStream();

        String line = reader.readLine();
        if (line == null) {
            return;
        }
        line = line.trim();
        System.out.println("recv nonce=" + line);

        String response;
        try {
            long nonce = Long.parseLong(line);
            byte[] result = JniUtils.getHandshake(nonce);
            response = toHex(result);
            System.out.println("send hex=" + response);
        } catch (Throwable t) {
            System.out.println("getHandshake failed:");
            t.printStackTrace(System.out);
            response = "ERROR";
        }

        out.write((response + "\n").getBytes(StandardCharsets.US_ASCII));
        out.flush();
    }

    private static String toHex(byte[] bytes) {
        if (bytes == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
