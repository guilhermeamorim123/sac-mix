package cn.upus.app.upprinting.dragx.ui.activity;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class RegistrationActivity extends Activity {
    private View setHomePromptLayout;
    private Button setHomeSettingsButton;
    private Button setHomeContinueButton;
    private View wifiPromptLayout;
    private Button wifiSettingsButton;
    private Button wifiContinueButton;
    private View formLayout;
    private View waitingLayout;
    private TextView waitingMessage;
    private EditText phoneField;
    private EditText companyField;
    private EditText emailField;
    private EditText contactField;
    private Button submitButton;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private static final long WIFI_POLL_INTERVAL_MS = 2000;
    private static final long SET_HOME_POLL_INTERVAL_MS = 2000;
    private Runnable wifiConnectivityPoll;
    private Runnable setHomePoll;

    // Hidden owner-only escape hatch: tap any of this screen's logos 7
    // times within 3 seconds to bring up a PIN prompt. Correct PIN skips
    // straight into the real app for testing, without any registration --
    // see RegistrationGate.markTestBypassEnabled for how this is meant to
    // be used and how it's undone (factory reset only).
    private static final int SECRET_TAP_COUNT = 7;
    private static final long SECRET_TAP_WINDOW_MS = 6000;
    private static final String TEST_BYPASS_PASSWORD = "160172";
    private int secretTapCounter = 0;
    private long secretTapWindowStart = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(getResources().getIdentifier("activity_registration", "layout", getPackageName()));

        setHomePromptLayout = findViewById(id("set_home_prompt_layout"));
        setHomeSettingsButton = findViewById(id("set_home_settings_button"));
        setHomeContinueButton = findViewById(id("set_home_continue_button"));
        wifiPromptLayout = findViewById(id("wifi_prompt_layout"));
        wifiSettingsButton = findViewById(id("wifi_settings_button"));
        wifiContinueButton = findViewById(id("wifi_continue_button"));
        formLayout = findViewById(id("form_layout"));
        waitingLayout = findViewById(id("waiting_layout"));
        waitingMessage = findViewById(id("waiting_message"));
        phoneField = findViewById(id("field_phone"));
        companyField = findViewById(id("field_company"));
        emailField = findViewById(id("field_email"));
        contactField = findViewById(id("field_contact"));
        submitButton = findViewById(id("submit_button"));

        submitButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                submitRegistration();
            }
        });

        wifiSettingsButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
                startWifiConnectivityPoll();
            }
        });

        wifiContinueButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                stopWifiConnectivityPoll();
                RegistrationGate.markWifiPromptShown(RegistrationActivity.this);
                renderForCurrentStatus();
            }
        });

        setHomeSettingsButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(Settings.ACTION_HOME_SETTINGS));
                startSetHomePoll();
            }
        });

        setHomeContinueButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                stopSetHomePoll();
                RegistrationGate.markSetHomePromptShown(RegistrationActivity.this);
                renderForCurrentStatus();
            }
        });

        View.OnClickListener secretTapListener = new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                onSecretLogoTap();
            }
        };
        int[] logoIds = {id("set_home_logo"), id("wifi_logo"), id("form_logo"), id("waiting_logo")};
        for (int logoId : logoIds) {
            ImageView logo = findViewById(logoId);
            if (logo != null) {
                logo.setOnClickListener(secretTapListener);
            }
        }
    }

    private void onSecretLogoTap() {
        long now = SystemClock.elapsedRealtime();
        if (now - secretTapWindowStart > SECRET_TAP_WINDOW_MS) {
            secretTapWindowStart = now;
            secretTapCounter = 0;
        }
        secretTapCounter++;
        if (secretTapCounter >= SECRET_TAP_COUNT) {
            secretTapCounter = 0;
            showTestBypassDialog();
        } else if (secretTapCounter >= 2) {
            // Feedback from the 2nd tap onward -- confirms taps are being
            // registered at all, without being an obvious "secret code"
            // hint to someone who wasn't already told about this feature.
            Toast.makeText(this, secretTapCounter + "/" + SECRET_TAP_COUNT, Toast.LENGTH_SHORT).show();
        }
    }

    private void showTestBypassDialog() {
        // Deliberately NOT using AlertDialog.Builder's setPositiveButton/
        // setNegativeButton -- on this hardware's narrower screen, the
        // stock two-button panel mis-measures and squeezes the positive
        // button ("Entrar") down to an ~18px sliver at the screen edge,
        // making it impossible to tap (confirmed live, 2026-07-21, via
        // uiautomator dump on a real machine). A custom, vertically
        // stacked layout with full-width buttons sidesteps that platform
        // quirk entirely, regardless of screen size.
        final EditText passwordField = new EditText(this);
        passwordField.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        container.setPadding(padding, padding, padding, padding);
        container.addView(passwordField);

        final AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Acesso de teste")
                .setMessage("Digite a senha para entrar sem cadastro:")
                .setView(container)
                .setCancelable(true)
                .create();

        Button enterButton = new Button(this);
        enterButton.setText("Entrar");
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        buttonParams.topMargin = (int) (16 * getResources().getDisplayMetrics().density);
        enterButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String entered = passwordField.getText().toString().trim();
                if (TEST_BYPASS_PASSWORD.equals(entered)) {
                    RegistrationGate.markTestBypassEnabled(RegistrationActivity.this);
                    Intent intent = new Intent(RegistrationActivity.this, InitActivity.class);
                    startActivity(intent);
                    finish();
                } else {
                    Toast.makeText(RegistrationActivity.this, "Senha incorreta.", Toast.LENGTH_SHORT).show();
                }
            }
        });
        container.addView(enterButton, buttonParams);

        Button cancelButton = new Button(this);
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

    @Override
    protected void onResume() {
        super.onResume();
        renderForCurrentStatus();
        RegistrationGate.startPolling(getApplicationContext());
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopWifiConnectivityPoll();
        stopSetHomePoll();
    }

    // This kiosk hardware has no navigation bar and no back/home button --
    // once the WiFi settings screen (a different app) is opened on top of
    // this one, there is no user-operable way back. Polling for
    // connectivity and forcibly reclaiming the foreground once a network
    // connects is the only reliable way back, and reuses the exact same
    // forced-navigation mechanism RegistrationGate.reactToStatusChange
    // already relies on elsewhere in this app.
    private void startWifiConnectivityPoll() {
        if (wifiConnectivityPoll != null) {
            return;
        }
        wifiConnectivityPoll = new Runnable() {
            @Override
            public void run() {
                if (isNetworkConnected()) {
                    stopWifiConnectivityPoll();
                    Intent intent = new Intent(getApplicationContext(), RegistrationActivity.class);
                    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                    startActivity(intent);
                } else {
                    mainHandler.postDelayed(this, WIFI_POLL_INTERVAL_MS);
                }
            }
        };
        mainHandler.postDelayed(wifiConnectivityPoll, WIFI_POLL_INTERVAL_MS);
    }

    private void stopWifiConnectivityPoll() {
        if (wifiConnectivityPoll != null) {
            mainHandler.removeCallbacks(wifiConnectivityPoll);
            wifiConnectivityPoll = null;
        }
    }

    private boolean isNetworkConnected() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo activeNetwork = cm.getActiveNetworkInfo();
        return activeNetwork != null && activeNetwork.isConnected();
    }

    // Same "no navigation bar, must poll and force our own way back" logic
    // as startWifiConnectivityPoll -- here we poll whether the system has
    // resolved DragX as the default HOME app yet, and reclaim the
    // foreground as soon as it has.
    private void startSetHomePoll() {
        if (setHomePoll != null) {
            return;
        }
        setHomePoll = new Runnable() {
            @Override
            public void run() {
                if (isDefaultHomeApp()) {
                    stopSetHomePoll();
                    Intent intent = new Intent(getApplicationContext(), RegistrationActivity.class);
                    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                    startActivity(intent);
                } else {
                    mainHandler.postDelayed(this, SET_HOME_POLL_INTERVAL_MS);
                }
            }
        };
        mainHandler.postDelayed(setHomePoll, SET_HOME_POLL_INTERVAL_MS);
    }

    private void stopSetHomePoll() {
        if (setHomePoll != null) {
            mainHandler.removeCallbacks(setHomePoll);
            setHomePoll = null;
        }
    }

    private boolean isDefaultHomeApp() {
        Intent homeIntent = new Intent(Intent.ACTION_MAIN);
        homeIntent.addCategory(Intent.CATEGORY_HOME);
        ResolveInfo resolveInfo = getPackageManager().resolveActivity(homeIntent, PackageManager.MATCH_DEFAULT_ONLY);
        return resolveInfo != null
                && resolveInfo.activityInfo != null
                && getPackageName().equals(resolveInfo.activityInfo.packageName);
    }

    private int id(String name) {
        return getResources().getIdentifier(name, "id", getPackageName());
    }

    private void renderForCurrentStatus() {
        String status = RegistrationGate.readStatus(this);
        if ("pending".equals(status)) {
            setHomePromptLayout.setVisibility(View.GONE);
            wifiPromptLayout.setVisibility(View.GONE);
            formLayout.setVisibility(View.GONE);
            waitingLayout.setVisibility(View.VISIBLE);
            waitingMessage.setText("Cadastro enviado. Aguardando aprovação...");
        } else if ("blocked".equals(status)) {
            setHomePromptLayout.setVisibility(View.GONE);
            wifiPromptLayout.setVisibility(View.GONE);
            formLayout.setVisibility(View.GONE);
            waitingLayout.setVisibility(View.VISIBLE);
            waitingMessage.setText("Esta máquina foi bloqueada. Entre em contato com o suporte.");
        } else if ("approved".equals(status)) {
            // Reaching this screen while already approved shouldn't
            // normally happen (RegistrationGate.launchNextScreen sends
            // approved machines straight to InitActivity) -- but handle it
            // defensively rather than showing a confusing blank state.
            startActivity(new android.content.Intent(this, InitActivity.class));
            finish();
        } else if (!RegistrationGate.wasSetHomePromptShown(this)) {
            // Never registered before, and the one-time "set DragX as the
            // default home app" prompt hasn't been dismissed yet -- show
            // it first of all, since this hardware has no navigation bar
            // and losing the home-app slot back to the vendor's original
            // app after a power cycle is exactly the failure this prompt
            // exists to prevent.
            setHomePromptLayout.setVisibility(View.VISIBLE);
            wifiPromptLayout.setVisibility(View.GONE);
            formLayout.setVisibility(View.GONE);
            waitingLayout.setVisibility(View.GONE);
            setHomeSettingsButton.requestFocus();
        } else if (!RegistrationGate.wasWifiPromptShown(this)) {
            // Never registered before, and the one-time WiFi prompt hasn't
            // been dismissed yet on this device -- show it ahead of the
            // form, since submitting the form needs a working connection
            // anyway and a brand-new machine at a new location has no
            // WiFi configured yet.
            setHomePromptLayout.setVisibility(View.GONE);
            wifiPromptLayout.setVisibility(View.VISIBLE);
            formLayout.setVisibility(View.GONE);
            waitingLayout.setVisibility(View.GONE);
            // Explicitly focus a view in the now-visible layout -- without
            // this, switching visibility between layouts at runtime (as
            // opposed to a layout being visible from the moment the
            // Activity is created) can leave nothing focused, which shows
            // an unwanted system scroll/focus affordance bar on this
            // hardware's Android build.
            wifiSettingsButton.requestFocus();
        } else {
            setHomePromptLayout.setVisibility(View.GONE);
            wifiPromptLayout.setVisibility(View.GONE);
            formLayout.setVisibility(View.VISIBLE);
            waitingLayout.setVisibility(View.GONE);
            phoneField.requestFocus();
        }
    }

    private void submitRegistration() {
        final String phone = phoneField.getText().toString().trim();
        final String company = companyField.getText().toString().trim();
        final String email = emailField.getText().toString().trim();
        final String contact = contactField.getText().toString().trim();

        if (phone.isEmpty() || company.isEmpty() || email.isEmpty() || contact.isEmpty()) {
            Toast.makeText(this, "Preencha todos os campos.", Toast.LENGTH_SHORT).show();
            return;
        }

        submitButton.setEnabled(false);

        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean success = RegistrationGate.submitRegistration(
                        RegistrationActivity.this, phone, company, email, contact);
                mainHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        submitButton.setEnabled(true);
                        if (success) {
                            // Clears any earlier failed attempt's stored data --
                            // otherwise the background retry (RegistrationGate's
                            // poller) would resend stale fields later even
                            // though this manual attempt already succeeded.
                            RegistrationGate.clearPendingSubmission(RegistrationActivity.this);
                            RegistrationGate.writeStatus(RegistrationActivity.this, "pending");
                            renderForCurrentStatus();
                        } else {
                            // Keep the four fields filled in -- design's
                            // Error handling section: don't silently lose
                            // what the customer typed. Also persist them so
                            // RegistrationGate's background poller can retry
                            // automatically without the customer needing to
                            // notice this failure and resubmit -- see
                            // docs/superpowers/specs/2026-07-27-registration-submission-retry-design.md.
                            RegistrationGate.savePendingSubmission(
                                    RegistrationActivity.this, phone, company, email, contact);
                            Toast.makeText(RegistrationActivity.this,
                                    "Não foi possível enviar o cadastro. Verifique a internet e tente novamente.",
                                    Toast.LENGTH_LONG).show();
                        }
                    }
                });
            }
        }).start();
    }
}
