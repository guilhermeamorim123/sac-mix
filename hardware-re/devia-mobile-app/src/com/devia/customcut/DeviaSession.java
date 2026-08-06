package com.devia.customcut;

import android.bluetooth.BluetoothDevice;

import java.util.ArrayList;
import java.util.List;

/**
 * Process-wide holder for the live Bluetooth connection, so the connect
 * screen and the cut screen can share one DeviaBluetoothLink instance
 * without re-serializing a live socket through Intent extras.
 *
 * Also owns the DeviaBluetoothLink.Listener registration: incoming lines
 * (identification responses, and eventually PGREADY/PGOK/PGERR) are
 * forwarded to whichever screen is currently visible (registered via
 * setActiveListener in onResume/onPause), and buffered otherwise so a
 * response that arrives while navigating between screens isn't lost
 * silently.
 */
public class DeviaSession implements DeviaBluetoothLink.Listener {

    private static final DeviaSession INSTANCE = new DeviaSession();

    private DeviaBluetoothLink link;
    private String deviceLabel;
    private String deviceAddress;
    private String deviceName;
    private DeviaBluetoothLink.Listener activeListener;
    private final List<String> buffer = new ArrayList<>();

    public static DeviaSession get() {
        return INSTANCE;
    }

    private DeviaSession() {
    }

    public void setLink(DeviaBluetoothLink link, BluetoothDevice device) {
        this.link = link;
        this.deviceAddress = device.getAddress();
        this.deviceName = device.getName();
        this.deviceLabel = device.getName() + " (" + device.getAddress() + ")";
    }

    public String getDeviceAddress() {
        return deviceAddress;
    }

    public String getDeviceNameOnly() {
        return deviceName;
    }

    public DeviaBluetoothLink getLink() {
        return link;
    }

    public String getDeviceLabel() {
        return deviceLabel;
    }

    public boolean isConnected() {
        return link != null;
    }

    public void disconnect() {
        if (link != null) {
            link.disconnect();
            link = null;
            deviceLabel = null;
            deviceAddress = null;
            deviceName = null;
        }
    }

    /** Call from onResume; also flushes anything buffered while no screen was listening. */
    public synchronized void setActiveListener(DeviaBluetoothLink.Listener listener) {
        activeListener = listener;
        for (String line : buffer) {
            listener.onLine(line);
        }
        buffer.clear();
    }

    /** Call from onPause. */
    public synchronized void clearActiveListener(DeviaBluetoothLink.Listener listener) {
        if (activeListener == listener) {
            activeListener = null;
        }
    }

    @Override
    public synchronized void onLine(String line) {
        if (activeListener != null) {
            activeListener.onLine(line);
        } else {
            buffer.add(line);
        }
    }

    @Override
    public void onError(Exception e) {
        if (activeListener != null) {
            activeListener.onError(e);
        }
    }

    @Override
    public void onDisconnected() {
        link = null;
        deviceLabel = null;
        if (activeListener != null) {
            activeListener.onDisconnected();
        }
    }
}
