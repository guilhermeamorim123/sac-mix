package cn.upus.app.upprinting.dragx.ui.activity;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.os.SystemClock;
import android.text.InputType;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;

/**
 * The reverse of RegistrationActivity's secret-tap gesture: reachable
 * from within the main app (wired onto SettingActivity's invisible
 * "view1" spacer, right next to the data-version label at the bottom of
 * the settings list -- an existing, purely decorative element, so this
 * adds no visible UI of its own). Same 7-taps-in-6-seconds gesture and
 * same PIN as the entry gesture; on success it exits test-bypass mode
 * and returns to the registration screen -- a lightweight alternative to
 * a full factory reset, which wipes the entire device (confirmed
 * 2026-07-21, not just app data).
 */
public class SecretExitTapListener implements View.OnClickListener {
    private static final int SECRET_TAP_COUNT = 7;
    private static final long SECRET_TAP_WINDOW_MS = 6000;
    private static final String EXIT_PASSWORD = "160172";

    private final Activity activity;
    private int tapCounter = 0;
    private long tapWindowStart = 0;

    public SecretExitTapListener(Activity activity) {
        this.activity = activity;
    }

    @Override
    public void onClick(View v) {
        long now = SystemClock.elapsedRealtime();
        if (now - tapWindowStart > SECRET_TAP_WINDOW_MS) {
            tapWindowStart = now;
            tapCounter = 0;
        }
        tapCounter++;
        if (tapCounter >= SECRET_TAP_COUNT) {
            tapCounter = 0;
            showExitDialog();
        } else {
            Toast.makeText(activity, tapCounter + "/" + SECRET_TAP_COUNT, Toast.LENGTH_SHORT).show();
        }
    }

    private void showExitDialog() {
        // See RegistrationActivity.showTestBypassDialog()'s comment --
        // same fix, same reason: the stock AlertDialog two-button panel
        // squeezes the positive button unusably small on this hardware's
        // narrower screen (confirmed live, 2026-07-21).
        final EditText passwordField = new EditText(activity);
        passwordField.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);

        LinearLayout container = new LinearLayout(activity);
        container.setOrientation(LinearLayout.VERTICAL);
        int padding = (int) (24 * activity.getResources().getDisplayMetrics().density);
        container.setPadding(padding, padding, padding, padding);
        container.addView(passwordField);

        final AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("Sair do modo de teste")
                .setMessage("Digite a senha para voltar ao cadastro:")
                .setView(container)
                .setCancelable(true)
                .create();

        Button confirmButton = new Button(activity);
        confirmButton.setText("Confirmar");
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        buttonParams.topMargin = (int) (16 * activity.getResources().getDisplayMetrics().density);
        confirmButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String entered = passwordField.getText().toString().trim();
                if (EXIT_PASSWORD.equals(entered)) {
                    RegistrationGate.clearTestBypassAndReturnToRegistration(activity);
                    activity.finish();
                } else {
                    Toast.makeText(activity, "Senha incorreta.", Toast.LENGTH_SHORT).show();
                }
            }
        });
        container.addView(confirmButton, buttonParams);

        Button cancelButton = new Button(activity);
        cancelButton.setText("Cancelar");
        cancelButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                dialog.dismiss();
            }
        });
        container.addView(cancelButton, buttonParams);

        dialog.show();
    }
}
