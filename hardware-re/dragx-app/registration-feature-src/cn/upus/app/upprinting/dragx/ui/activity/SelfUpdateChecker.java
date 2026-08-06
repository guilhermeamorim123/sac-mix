package cn.upus.app.upprinting.dragx.ui.activity;

import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;
import com.blankj.utilcode.util.AppUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

/**
 * Checks our own fleet panel's /v1/api/ver01/app_upgrade endpoint directly,
 * bypassing the vendor's MainActivity.a0()/UpdateTipDialog/update_mark
 * chain entirely -- that chain silently stops offering an already-seen
 * (appVersion, binVersion) pair once MApp.C ("forcedUpdate", set from the
 * VENDOR's own real backend, outside our control) is "1". Called from
 * RegistrationGate's existing 3-minute poll thread, so this runs
 * regardless of what screen is in the foreground and regardless of
 * anything the vendor's backend decides.
 */
public class SelfUpdateChecker {
    private static final String TAG = "SelfUpdateChecker";
    private static final String PANEL_BASE_URL = "https://dragx-fleet-panel.onrender.com";
    // Same shared secret as RegistrationGate's API_KEY / the panel's
    // CHECKIN_API_KEY env var -- substituted at build time, never
    // committed here.
    private static final String API_KEY = "__CHECKIN_API_KEY__";

    public static void checkForUpdate(Context appContext) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(PANEL_BASE_URL + "/v1/api/ver01/app_upgrade");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);
            String body = "appVersion=" + URLEncoder.encode(String.valueOf(AppUtils.getAppVersionCode()), "UTF-8");
            conn.getOutputStream().write(body.getBytes(StandardCharsets.UTF_8));
            conn.getOutputStream().close();

            int code = conn.getResponseCode();
            if (code != 200) {
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

            JSONObject root = new JSONObject(sb.toString());
            JSONObject data = root.optJSONObject("data");
            if (data == null) {
                return;
            }
            JSONArray bussData = data.optJSONArray("bussData");
            if (bussData == null || bussData.length() == 0) {
                return;
            }
            JSONObject release = bussData.getJSONObject(0);
            int newVersionCode = release.getInt("appVersion");
            if (newVersionCode <= AppUtils.getAppVersionCode()) {
                return;
            }

            Intent intent = new Intent(appContext, SelfUpdateActivity.class);
            intent.putExtra("appVersionName", release.optString("appVersionName", ""));
            intent.putExtra("appFilePath", release.getString("appFilePath"));
            intent.putExtra("appFileMd5", release.optString("appFileMd5", ""));
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            appContext.startActivity(intent);
        } catch (Exception e) {
            Log.w(TAG, "self-update check failed, will retry next poll", e);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /**
     * Reports this device's serial + installed app version to the fleet
     * panel's existing /api/machines/checkin endpoint (already built,
     * already deployed, never previously called by the app). Gives the
     * panel real visibility into which machines are still on an old
     * (pre-package-rename) build versus the current one, instead of
     * having to check each machine physically.
     */
    public static void reportCheckin() {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(PANEL_BASE_URL + "/api/machines/checkin");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("X-Api-Key", API_KEY);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);

            JSONObject body = new JSONObject();
            body.put("serial", Build.SERIAL);
            body.put("dragx_version", AppUtils.getAppVersionName());

            OutputStream out = conn.getOutputStream();
            out.write(body.toString().getBytes(StandardCharsets.UTF_8));
            out.close();
            conn.getResponseCode();
        } catch (Exception e) {
            Log.w(TAG, "checkin report failed, will retry next poll", e);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }
}
