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
import java.io.OutputStream;
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
    private static final String PREF_KEY_WIFI_PROMPT_SHOWN = "wifi_prompt_shown";
    private static final String PREF_KEY_SET_HOME_PROMPT_SHOWN = "set_home_prompt_shown";
    private static final String PREF_KEY_TEST_BYPASS = "test_bypass_enabled";
    private static final String PREF_KEY_PENDING_PHONE = "pending_submission_phone";
    private static final String PREF_KEY_PENDING_COMPANY = "pending_submission_company";
    private static final String PREF_KEY_PENDING_EMAIL = "pending_submission_email";
    private static final String PREF_KEY_PENDING_CONTACT = "pending_submission_contact";
    private static final long POLL_INTERVAL_MS = 3 * 60 * 1000;

    private static volatile boolean pollingStarted = false;
    private static final Handler handler = new Handler(Looper.getMainLooper());

    public static void launchNextScreen(Context context) {
        startPolling(context.getApplicationContext());
        if (wasTestBypassEnabled(context)) {
            // Owner-only local override (see RegistrationActivity's hidden
            // tap gesture) -- lets the owner fully test a machine before
            // handing it to a real customer, without any real registration
            // or remote approval. Deliberately NOT reversible from within
            // the app: the only way back to the registration screen is a
            // full factory reset (which wipes this SharedPreferences flag
            // along with everything else), so a machine can never
            // accidentally ship to a customer still in test mode without a
            // very deliberate, hard-to-miss reset step first.
            context.startActivity(new Intent(context, InitActivity.class));
            return;
        }
        String status = readStatus(context);
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

    // Whether the one-time "connect this machine to WiFi" prompt has
    // already been shown and dismissed on this device. Tracked separately
    // from PREF_KEY_STATUS so it stays true forever once shown, even
    // across app restarts, regardless of what registration_status later
    // becomes.
    public static boolean wasWifiPromptShown(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getBoolean(PREF_KEY_WIFI_PROMPT_SHOWN, false);
    }

    public static void markWifiPromptShown(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putBoolean(PREF_KEY_WIFI_PROMPT_SHOWN, true).apply();
    }

    // Same one-time-ever tracking as wasWifiPromptShown, for the "set
    // DragX as the default home app" prompt shown even earlier in the
    // first-launch flow (this hardware has no navigation bar, so without
    // this the app can silently lose the home-app slot back to the
    // vendor's original app after a power cycle).
    public static boolean wasSetHomePromptShown(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getBoolean(PREF_KEY_SET_HOME_PROMPT_SHOWN, false);
    }

    public static void markSetHomePromptShown(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putBoolean(PREF_KEY_SET_HOME_PROMPT_SHOWN, true).apply();
    }

    public static boolean wasTestBypassEnabled(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getBoolean(PREF_KEY_TEST_BYPASS, false);
    }

    public static void markTestBypassEnabled(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putBoolean(PREF_KEY_TEST_BYPASS, true).apply();
    }

    /**
     * Shared HTTP POST logic for the registration form, used by both the
     * manual "Enviar Cadastro" button (RegistrationActivity.doSubmit())
     * and the background retry below -- one place for the request shape,
     * so the two callers can never drift apart. Same URL, headers, JSON
     * fields and timeouts RegistrationActivity used before this was
     * extracted. Returns true only on HTTP 200.
     */
    public static boolean submitRegistration(Context context, String phone, String company, String email, String contact) {
        HttpURLConnection conn = null;
        try {
            JSONObject payload = new JSONObject();
            payload.put("serial", Build.SERIAL);
            payload.put("phone", phone);
            payload.put("company_name", company);
            payload.put("email", email);
            payload.put("contact_name", contact);

            URL url = new URL(PANEL_BASE_URL + "/api/machines/register");
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

    /**
     * Persists a registration submission that failed to send, so the
     * background poller can retry it later without the customer needing
     * to notice the failure and manually resubmit -- see
     * docs/superpowers/specs/2026-07-27-registration-submission-retry-design.md.
     */
    public static void savePendingSubmission(Context context, String phone, String company, String email, String contact) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
                .putString(PREF_KEY_PENDING_PHONE, phone)
                .putString(PREF_KEY_PENDING_COMPANY, company)
                .putString(PREF_KEY_PENDING_EMAIL, email)
                .putString(PREF_KEY_PENDING_CONTACT, contact)
                .apply();
    }

    public static void clearPendingSubmission(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
                .remove(PREF_KEY_PENDING_PHONE)
                .remove(PREF_KEY_PENDING_COMPANY)
                .remove(PREF_KEY_PENDING_EMAIL)
                .remove(PREF_KEY_PENDING_CONTACT)
                .apply();
    }

    public static boolean hasPendingSubmission(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.contains(PREF_KEY_PENDING_PHONE);
    }

    /**
     * Reverses markTestBypassEnabled -- reachable from a hidden gesture in
     * SettingActivity (same secret-tap pattern as RegistrationActivity's
     * entry gesture) so the owner can back out of test mode and return to
     * the very beginning of the first-launch flow, without a full factory
     * reset (which wipes the whole app and every other setting on the
     * device -- confirmed 2026-07-21). Clears every one-time-shown flag,
     * not just the bypass/status pair, so the device lands on the very
     * first screen (set-home-app prompt) rather than skipping ahead to
     * whichever screen it happened to leave off at -- explicit owner
     * preference (2026-07-21): re-doing the whole flow from scratch is
     * more useful for testing than jumping straight to the registration
     * form.
     */
    public static void clearTestBypassAndReturnToRegistration(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
                .putBoolean(PREF_KEY_TEST_BYPASS, false)
                .putBoolean(PREF_KEY_SET_HOME_PROMPT_SHOWN, false)
                .putBoolean(PREF_KEY_WIFI_PROMPT_SHOWN, false)
                .remove(PREF_KEY_STATUS)
                .apply();
        Intent intent = new Intent(context, RegistrationActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        context.startActivity(intent);
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
                // Independent of the status check below -- doesn't share
                // its connection, its failure never affects registration
                // status handling, and vice versa. See
                // docs/superpowers/specs/2026-07-20-dragx-self-update-design.md
                // for why this bypasses the vendor's own (unreliable)
                // update-check chain entirely.
                SelfUpdateChecker.checkForUpdate(appContext);
                SelfUpdateChecker.reportCheckin();
                retryPendingSubmissionIfAny(appContext);

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

    /**
     * Independent of the status-check block below (same "one failure
     * never affects the other" reasoning as SelfUpdateChecker's calls
     * above) -- retries a registration submission that failed earlier,
     * with no attempt cap, same philosophy as the status/self-update
     * checks that keep trying every cycle indefinitely. See
     * docs/superpowers/specs/2026-07-27-registration-submission-retry-design.md.
     */
    private static void retryPendingSubmissionIfAny(final Context appContext) {
        if (!hasPendingSubmission(appContext)) {
            return;
        }
        SharedPreferences prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String phone = prefs.getString(PREF_KEY_PENDING_PHONE, null);
        String company = prefs.getString(PREF_KEY_PENDING_COMPANY, null);
        String email = prefs.getString(PREF_KEY_PENDING_EMAIL, null);
        String contact = prefs.getString(PREF_KEY_PENDING_CONTACT, null);
        if (submitRegistration(appContext, phone, company, email, contact)) {
            clearPendingSubmission(appContext);
            handler.post(new Runnable() {
                @Override
                public void run() {
                    // Same "force back to RegistrationActivity" mechanism
                    // reactToStatusChange() uses for a remote status
                    // change -- shows "Aguardando aprovação..." instead of
                    // the stale form, even if the customer walked away.
                    Intent intent = new Intent(appContext, RegistrationActivity.class);
                    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                    appContext.startActivity(intent);
                }
            });
        }
        // else: leave it stored, retry again next poll cycle.
    }

    private static void reactToStatusChange(Context appContext, String newStatus) {
        if (wasTestBypassEnabled(appContext)) {
            // Test-mode machines never get pulled back to the
            // registration/waiting screen by a remote status change --
            // the owner's local override always wins until a factory
            // reset. Still fine to keep polling (harmless, no UI effect).
            return;
        }
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
