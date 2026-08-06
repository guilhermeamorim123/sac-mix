package cn.upus.app.upprinting.dragx.ui.activity;

import android.os.Build;
import android.util.Log;

import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Reports one real cut to the fleet panel's cut-balance counter (see
 * docs/superpowers/specs/2026-07-17-cut-balance-design.md) -- a usage
 * counter, not a gate, so a failed report here must never affect the cut
 * that already physically happened. Called from the two exact call sites
 * where FilmCutActivity/CustomCutActivity dispatch the real cut command to
 * the cutting hardware, which fire unconditionally regardless of the
 * vendor's own (unrelated, already-bypassed) billing-mode setting.
 */
public class CutReporter {
    private static final String TAG = "CutReporter";
    private static final String PANEL_BASE_URL = "https://dragx-fleet-panel.onrender.com";
    // Substituted for the real value at build time -- see
    // RegistrationGate's identical constant for the full explanation.
    private static final String API_KEY = "__CHECKIN_API_KEY__";

    public static void reportCut() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                HttpURLConnection conn = null;
                try {
                    URL url = new URL(PANEL_BASE_URL + "/api/machines/" + Build.SERIAL + "/cut");
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("X-Api-Key", API_KEY);
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(15000);
                    conn.getResponseCode();
                } catch (Exception e) {
                    Log.w(TAG, "cut report failed, ignoring", e);
                } finally {
                    if (conn != null) {
                        conn.disconnect();
                    }
                }
            }
        }).start();
    }
}
