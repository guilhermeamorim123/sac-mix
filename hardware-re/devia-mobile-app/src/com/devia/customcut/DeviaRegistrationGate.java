package com.devia.customcut;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Registration/approval gate for this app, mirroring DragX's own
 * RegistrationGate (cn.upus.app.upprinting.dragx.ui.activity.
 * RegistrationGate) but talking to the NEW, isolated /api/devia/machines/*
 * endpoints and keyed by Bluetooth address instead of Build.SERIAL --
 * see models.DeviaMachine in the fleet-panel project for why this is a
 * separate table, not a reuse of the CUTTER_E326 `machines` table.
 *
 * Same fleet-panel deployment and shared secret as DragX (this app is a
 * new client of the same panel, not a new backend) -- API_KEY is
 * substituted for the real CHECKIN_API_KEY value at build time, never
 * committed here, same convention as DragX's own RegistrationGate.
 */
public class DeviaRegistrationGate {
    private static final String TAG = "DeviaRegistrationGate";
    private static final String PANEL_BASE_URL = "https://dragx-fleet-panel.onrender.com";
    private static final String API_KEY = "__CHECKIN_API_KEY__";
    private static final String PREFS_NAME = "devia_registration_gate_prefs";
    private static final String PREF_KEY_STATUS = "registration_status";
    private static final long POLL_INTERVAL_MS = 3 * 60 * 1000;

    private static volatile boolean pollingStarted = false;
    private static final Handler handler = new Handler(Looper.getMainLooper());

    public static String readStatus(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(PREF_KEY_STATUS, "");
    }

    public static void writeStatus(Context context, String status) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString(PREF_KEY_STATUS, status).apply();
    }

    /**
     * Blocking HTTP POST to /api/devia/machines/register -- call from a
     * background thread. Returns true only on HTTP 200. Same request
     * shape as DragX's RegistrationGate.submitRegistration.
     */
    public static boolean submitRegistration(String bluetoothAddress, String deviceName,
                                              String phone, String company, String email, String contact) {
        HttpURLConnection conn = null;
        try {
            JSONObject payload = new JSONObject();
            payload.put("bluetooth_address", bluetoothAddress);
            payload.put("device_name", deviceName);
            payload.put("phone", phone);
            payload.put("company_name", company);
            payload.put("email", email);
            payload.put("contact_name", contact);

            URL url = new URL(PANEL_BASE_URL + "/api/devia/machines/register");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setRequestProperty("X-Api-Key", API_KEY);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);
            conn.setDoOutput(true);

            OutputStream os = conn.getOutputStream();
            os.write(payload.toString().getBytes(StandardCharsets.UTF_8));
            os.close();

            return conn.getResponseCode() == 200;
        } catch (Exception e) {
            return false;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /** Sentinel returned by fetchStatus for a confirmed HTTP 404 (this
     * address has never been registered) -- distinct from null, which means
     * the request itself failed (offline/timeout/unreachable) and the
     * caller should keep showing whatever it last knew, not the
     * registration form. */
    public static final String NOT_REGISTERED = "__not_registered__";

    /**
     * Blocking HTTP GET of the current status -- call from a background
     * thread. Returns the status string ("pending"/"approved"/"blocked"),
     * NOT_REGISTERED on a confirmed 404, or null if the request itself
     * failed (offline, panel unreachable) -- caller should keep the last
     * known local state on null, same "never block/unblock on an absent
     * response" rule as DragX's.
     */
    public static String fetchStatus(String bluetoothAddress) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(PANEL_BASE_URL + "/api/devia/machines/" + bluetoothAddress + "/status");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("X-Api-Key", API_KEY);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);
            int code = conn.getResponseCode();
            if (code == 404) {
                return NOT_REGISTERED;
            }
            if (code != 200) {
                return null;
            }
            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            reader.close();
            return new JSONObject(sb.toString()).getString("status");
        } catch (Exception e) {
            Log.w(TAG, "status fetch failed, keeping last known state", e);
            return null;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /**
     * Starts the background poller (idempotent, safe to call repeatedly --
     * only the first call per process actually schedules anything). If the
     * remote status ever changes to "blocked"/"pending" while some other
     * screen is in the foreground, forces the user back to
     * RegistrationActivity, same as DragX's reactToStatusChange.
     */
    public static synchronized void startPolling(final Context appContext, final String bluetoothAddress) {
        if (pollingStarted) {
            return;
        }
        pollingStarted = true;
        scheduleNextPoll(appContext, bluetoothAddress);
    }

    private static void scheduleNextPoll(final Context appContext, final String bluetoothAddress) {
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                pollOnce(appContext, bluetoothAddress);
                scheduleNextPoll(appContext, bluetoothAddress);
            }
        }, POLL_INTERVAL_MS);
    }

    private static void pollOnce(final Context appContext, final String bluetoothAddress) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                String newStatus = fetchStatus(bluetoothAddress);
                if (newStatus == null) {
                    return;
                }
                String oldStatus = readStatus(appContext);
                writeStatus(appContext, newStatus);
                if (!newStatus.equals(oldStatus) && ("blocked".equals(newStatus) || "pending".equals(newStatus))) {
                    final String statusForUi = newStatus;
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            Intent intent = new Intent(appContext, RegistrationActivity.class);
                            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                            intent.putExtra("bluetoothAddress", bluetoothAddress);
                            appContext.startActivity(intent);
                        }
                    });
                }
            }
        }, "DeviaRegistrationPoll").start();
    }
}
