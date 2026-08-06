package com.devia.customcut;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

/**
 * Bluetooth Classic RFCOMM/SPP transport, confirmed against a live capture
 * of the real Devia app this session (same UUID, same SDP negotiation).
 * Identification commands (;RHVER; etc) are sent as plain ASCII, one write
 * per command, matching what was captured live. Cut-job payloads are sent
 * chunked (2048 bytes/chunk, 100ms apart) matching SendBluetoothService in
 * the real app.
 */
public class DeviaBluetoothLink {

    private static final UUID SPP_UUID =
            UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
    private static final int CHUNK_SIZE = 2048;
    private static final long CHUNK_DELAY_MS = 100;

    public interface Listener {
        void onLine(String line);
        void onError(Exception e);
        void onDisconnected();
    }

    private final BluetoothDevice device;
    private final Listener listener;
    private BluetoothSocket socket;
    private OutputStream out;
    private Thread readThread;
    private volatile boolean running;

    public DeviaBluetoothLink(BluetoothDevice device, Listener listener) {
        this.device = device;
        this.listener = listener;
    }

    /** Blocking connect -- call from a background thread, not the UI thread. */
    public void connect() throws IOException {
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter != null && adapter.isDiscovering()) {
            // an in-progress scan is a well-known cause of RFCOMM connect
            // failing with "read failed, socket might closed or timeout"
            adapter.cancelDiscovery();
        }

        socket = device.createRfcommSocketToServiceRecord(SPP_UUID);
        try {
            socket.connect();
        } catch (IOException standardFailure) {
            // fallback: some Android/chipset combos only work through the
            // hidden channel-based API instead of the SDP-based one above,
            // even though the real Devia app itself uses the SDP path --
            // channel 1 is the SPP default and matches this project's own
            // earlier BtProbe3.java precedent for this exact failure mode.
            try {
                socket.close();
            } catch (IOException ignored) {
            }
            try {
                Method m = device.getClass().getMethod("createRfcommSocket", int.class);
                socket = (BluetoothSocket) m.invoke(device, 1);
                socket.connect();
            } catch (Exception fallbackFailure) {
                throw standardFailure;
            }
        }
        out = socket.getOutputStream();
        final InputStream in = socket.getInputStream();
        running = true;
        readThread = new Thread("DeviaBluetoothRead") {
            @Override
            public void run() {
                readLoop(in);
            }
        };
        readThread.start();
    }

    private void readLoop(InputStream in) {
        byte[] buf = new byte[1024];
        StringBuilder pending = new StringBuilder();
        try {
            while (running) {
                int n = in.read(buf);
                if (n < 0) break;
                pending.append(new String(buf, 0, n, StandardCharsets.US_ASCII));
                // responses are ';'-terminated tokens, e.g. "HVER=V7.1202;"
                int idx;
                while ((idx = pending.indexOf(";")) >= 0) {
                    String line = pending.substring(0, idx + 1);
                    pending.delete(0, idx + 1);
                    if (listener != null) listener.onLine(line);
                }
            }
        } catch (IOException e) {
            if (running && listener != null) listener.onError(e);
        } finally {
            running = false;
            if (listener != null) listener.onDisconnected();
        }
    }

    /** Sends a short plain-text command as-is (identification/config commands). */
    public void sendCommand(String command) throws IOException {
        out.write(command.getBytes(StandardCharsets.US_ASCII));
        out.flush();
    }

    /**
     * Sends a large payload (a cut-job command string) in 2048-byte chunks
     * with a 100ms pause between chunks, matching SendBluetoothService in
     * the real app. Blocking -- call from a background thread.
     */
    public void sendCutJob(String payload) throws IOException, InterruptedException {
        byte[] bytes = payload.getBytes(StandardCharsets.US_ASCII);
        int offset = 0;
        while (offset < bytes.length) {
            int len = Math.min(CHUNK_SIZE, bytes.length - offset);
            out.write(bytes, offset, len);
            out.flush();
            offset += len;
            if (offset < bytes.length) {
                Thread.sleep(CHUNK_DELAY_MS);
            }
        }
    }

    public void disconnect() {
        running = false;
        try {
            if (socket != null) socket.close();
        } catch (IOException ignored) {
        }
    }
}
