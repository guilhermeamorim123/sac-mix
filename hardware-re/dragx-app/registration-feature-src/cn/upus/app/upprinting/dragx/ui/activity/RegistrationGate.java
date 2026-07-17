package cn.upus.app.upprinting.dragx.ui.activity;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Single entry point for the registration/approval gate. Called once per
 * process from a small patch inserted into InitActivity.p(Context) (see
 * Task 5) -- decides whether to proceed to the normal app (InitActivity)
 * or show the registration/waiting screen (RegistrationActivity), and
 * starts the background status poller either way (it must keep running
 * even once approved, to catch a later remote block -- see
 * docs/superpowers/specs/2026-07-06-customer-registration-design.md).
 */
public class RegistrationGate {
    private static final String TAG = "RegistrationGate";
    private static final String PANEL_BASE_URL = "https://dragx-fleet-panel.onrender.com";
    // Same shared secret as the fleet panel's CHECKIN_API_KEY environment
    // variable (hardware-re/fleet-panel/README.md) -- substituted for the
    // real value at build time (Task 4), never committed here. Same
    // accepted tradeoff as other embedded secrets in this project (e.g.
    // the release keystore password) -- a small-scale internal tool, not
    // a security product.
    private static final String API_KEY = "__CHECKIN_API_KEY__";
    private static final String PREFS_NAME = "registration_gate_prefs";
    private static final String PREF_KEY_STATUS = "registration_status";
    private static final long POLL_INTERVAL_MS = 3 * 60 * 1000;

    private static volatile boolean pollingStarted = false;
    private static final Handler handler = new Handler(Looper.getMainLooper());

    public static void launchNextScreen(Context context) {
        String status = readStatus(context);
        startPolling(context.getApplicationContext());
        if ("approved".equals(status)) {
            context.startActivity(new Intent(context, InitActivity.class));
        } else {
            context.startActivity(new Intent(context, RegistrationActivity.class));
        }
    }

    public static String readStatus(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(PREF_KEY_STATUS, "");
    }

    public static void writeStatus(Context context, String status) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString(PREF_KEY_STATUS, status).apply();
    }

    public static synchronized void startPolling(final Context appContext) {
        if (pollingStarted) {
            return;
        }
        pollingStarted = true;
        scheduleNextPoll(appContext);
    }

    private static void scheduleNextPoll(final Context appContext) {
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                pollOnce(appContext);
                scheduleNextPoll(appContext);
            }
        }, POLL_INTERVAL_MS);
    }

    private static void pollOnce(final Context appContext) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                HttpURLConnection conn = null;
                try {
                    URL url = new URL(PANEL_BASE_URL + "/api/machines/" + Build.SERIAL + "/status");
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setRequestProperty("X-Api-Key", API_KEY);
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(15000);
                    int code = conn.getResponseCode();
                    if (code != 200) {
                        // Offline / panel unreachable / unknown serial --
                        // keep last known local state (see design's
                        // Offline behavior section). Never block or
                        // unblock based on an absent/failed response.
                        return;
                    }
                    BufferedReader reader = new BufferedReader(
                            new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sb.append(line);
                    }
                    reader.close();
                    JSONObject body = new JSONObject(sb.toString());
                    final String newStatus = body.getString("status");
                    String oldStatus = readStatus(appContext);
                    writeStatus(appContext, newStatus);
                    if (!newStatus.equals(oldStatus)) {
                        handler.post(new Runnable() {
                            @Override
                            public void run() {
                                reactToStatusChange(appContext, newStatus);
                            }
                        });
                    }
                } catch (Exception e) {
                    Log.w(TAG, "status poll failed, keeping last known state", e);
                } finally {
                    if (conn != null) {
                        conn.disconnect();
                    }
                }
            }
        }).start();
    }

    private static void reactToStatusChange(Context appContext, String newStatus) {
        if ("blocked".equals(newStatus) || "pending".equals(newStatus)) {
            // Force the user back to the gate from wherever they currently
            // are. FLAG_ACTIVITY_NEW_TASK is required since appContext is
            // not an Activity context; FLAG_ACTIVITY_CLEAR_TASK drops
            // whatever screen (catalog, cut screen, etc.) was on top.
            Intent intent = new Intent(appContext, RegistrationActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            appContext.startActivity(intent);
        } else if ("approved".equals(newStatus)) {
            // The machine just got approved. If RegistrationActivity is
            // currently the foreground screen (the customer submitted the
            // form and is sitting on "Aguardando aprovação..."), its own
            // onResume won't re-fire on its own -- there's no lifecycle
            // event to trigger it while it's already resumed. Force the
            // transition into the real app here instead, the same way the
            // blocked/pending case forces the opposite transition. If some
            // OTHER screen is already in the foreground (this poll cycle
            // landed after the user was already let further into the app
            // some other way), this is a harmless no-op on top of an
            // already-visible, already-working screen.
            Intent intent = new Intent(appContext, InitActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            appContext.startActivity(intent);
        }
    }
}
