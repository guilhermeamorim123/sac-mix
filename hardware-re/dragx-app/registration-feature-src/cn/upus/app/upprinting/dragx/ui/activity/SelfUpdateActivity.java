package cn.upus.app.upprinting.dragx.ui.activity;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;
import androidx.core.content.FileProvider;
import java.io.File;
import java.io.InputStream;
import java.io.RandomAccessFile;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;

/**
 * Dialog-themed activity launched by SelfUpdateChecker when the fleet
 * panel reports a newer DragX build than the one installed. Deliberately
 * has no dismissal memory -- if the user taps "Depois", this activity
 * just finishes and the same prompt will reappear on the next 3-minute
 * poll cycle for as long as the installed version stays behind. That is
 * the whole point: unlike the vendor's own update_mark cache, an
 * available update can never get silently and permanently swallowed.
 */
public class SelfUpdateActivity extends Activity {
    private static final String TAG = "SelfUpdateActivity";
    private static final int CHUNK_SIZE = 512 * 1024;
    private static final int MAX_RETRIES_PER_CHUNK = 5;
    // Dedicated FileProvider, declared fresh in the manifest, never used
    // under any other name in any prior build -- deliberately NOT reusing
    // AppUtils.installApp()/the existing utilcode.fileprovider, since that
    // one's authority had to change when the app's package was renamed
    // (cn.upus.app.upprinting.dragx -> com.dragx.app) and confirmed live
    // (2026-07-21, logcat) that changing a provider's authority between
    // versions during an in-place update breaks FileProvider's metadata
    // lookup, crashing the whole process. A brand-new authority sidesteps
    // that in-place-rename problem entirely, now and in any future rename.
    private static final String FILE_PROVIDER_AUTHORITY = "com.dragx.app.selfupdate.fileprovider";

    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        final String appVersionName = getIntent().getStringExtra("appVersionName");
        final String appFilePath = getIntent().getStringExtra("appFilePath");
        final String appFileMd5 = getIntent().getStringExtra("appFileMd5");

        new AlertDialog.Builder(this)
                .setTitle("Atualização disponível")
                .setMessage("Nova versão disponível: " + appVersionName + "\nAtualizar agora?")
                .setCancelable(false)
                .setPositiveButton("Atualizar agora", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        startDownload(appFilePath, appFileMd5);
                    }
                })
                .setNegativeButton("Depois", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        finish();
                    }
                })
                .setOnDismissListener(new DialogInterface.OnDismissListener() {
                    @Override
                    public void onDismiss(DialogInterface dialog) {
                        finish();
                    }
                })
                .show();
    }

    private void startDownload(final String urlStr, final String expectedMd5) {
        Toast.makeText(this, "Baixando atualização...", Toast.LENGTH_LONG).show();
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    File outFile = new File(getFilesDir(), "dragx_self_update.apk");
                    downloadInChunks(urlStr, outFile);

                    if (!expectedMd5.isEmpty() && !md5Of(outFile).equalsIgnoreCase(expectedMd5)) {
                        outFile.delete();
                        Log.w(TAG, "downloaded file MD5 mismatch, discarding (will retry next poll)");
                        mainHandler.post(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(SelfUpdateActivity.this, "Falha ao baixar atualização, tentando de novo mais tarde.", Toast.LENGTH_LONG).show();
                                finish();
                            }
                        });
                        return;
                    }

                    mainHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            installApk(outFile);
                            // Deliberately NOT calling finish() here -- on
                            // this hardware (Android 7.1.2), finishing this
                            // activity immediately after starting the
                            // installer intent raced with the installer's
                            // own activity actually coming to the
                            // foreground, so the confirmation screen never
                            // visibly appeared (confirmed live, 2026-07-21:
                            // the installer process started and was then
                            // reclaimed as "empty" a moment later, with no
                            // UI ever shown). Leaving this activity alive
                            // gives the installer time to take over the
                            // foreground properly; the user backing out of
                            // the installer naturally returns here, and the
                            // next poll cycle will simply re-offer the
                            // update if it still wasn't installed.
                        }
                    });
                } catch (Exception e) {
                    Log.w(TAG, "self-update download failed, will retry next poll", e);
                    mainHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(SelfUpdateActivity.this, "Falha ao baixar atualização, tentando de novo mais tarde.", Toast.LENGTH_LONG).show();
                            finish();
                        }
                    });
                }
            }
        }).start();
    }

    private void installApk(File apkFile) {
        try {
            // Deliberately mirrors the vendor's own IntentUtils.
            // getInstallAppIntent(File) exactly (same ACTION_VIEW + type +
            // flags) -- that code already works elsewhere in this app, so
            // an extra explicit grantUriPermission() loop tried earlier
            // tonight was solving the wrong problem (it hit the identical
            // "does not have permission" error, just from our own call
            // instead of the installer's). The real cause looked like
            // accumulated stale URI-permission state on this one
            // heavily-reused test device after many repeated identical
            // installs in one session, not a flag this code was missing.
            Uri contentUri = FileProvider.getUriForFile(this, FILE_PROVIDER_AUTHORITY, apkFile);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(contentUri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception e) {
            Log.w(TAG, "could not launch installer, will retry next poll", e);
        }
    }

    private void downloadInChunks(String urlStr, File outFile) throws Exception {
        long totalSize = probeTotalSize(urlStr);
        RandomAccessFile raf = new RandomAccessFile(outFile, "rw");
        raf.setLength(totalSize);
        long downloaded = 0;
        while (downloaded < totalSize) {
            long start = downloaded;
            long end = Math.min(start + CHUNK_SIZE - 1, totalSize - 1);
            byte[] chunk = downloadChunkWithRetry(urlStr, start, end);
            raf.seek(start);
            raf.write(chunk);
            downloaded += chunk.length;
        }
        raf.close();
    }

    private long probeTotalSize(String urlStr) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
        conn.setRequestMethod("HEAD");
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);
        conn.setInstanceFollowRedirects(true);
        long length = conn.getContentLengthLong();
        conn.disconnect();
        if (length <= 0) {
            throw new Exception("could not determine file size");
        }
        return length;
    }

    private byte[] downloadChunkWithRetry(String urlStr, long start, long end) throws Exception {
        Exception lastError = null;
        for (int attempt = 1; attempt <= MAX_RETRIES_PER_CHUNK; attempt++) {
            try {
                return downloadChunk(urlStr, start, end);
            } catch (Exception e) {
                lastError = e;
            }
        }
        throw lastError;
    }

    private byte[] downloadChunk(String urlStr, long start, long end) throws Exception {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) new URL(urlStr).openConnection();
            conn.setRequestProperty("Range", "bytes=" + start + "-" + end);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);
            conn.setInstanceFollowRedirects(true);
            InputStream in = conn.getInputStream();
            int expectedLength = (int) (end - start + 1);
            byte[] buffer = new byte[expectedLength];
            int totalRead = 0;
            while (totalRead < expectedLength) {
                int read = in.read(buffer, totalRead, expectedLength - totalRead);
                if (read == -1) {
                    break;
                }
                totalRead += read;
            }
            in.close();
            if (totalRead != expectedLength) {
                byte[] trimmed = new byte[totalRead];
                System.arraycopy(buffer, 0, trimmed, 0, totalRead);
                return trimmed;
            }
            return buffer;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    private static String md5Of(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("MD5");
        java.io.FileInputStream fis = new java.io.FileInputStream(file);
        byte[] buffer = new byte[8192];
        int read;
        while ((read = fis.read(buffer)) != -1) {
            digest.update(buffer, 0, read);
        }
        fis.close();
        byte[] hash = digest.digest();
        StringBuilder sb = new StringBuilder();
        for (byte b : hash) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
