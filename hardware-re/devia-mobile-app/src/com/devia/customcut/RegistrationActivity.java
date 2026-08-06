package com.devia.customcut;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Registration/approval gate screen -- shown after ConnectActivity connects
 * and before the customer reaches CutActivity/BrandActivity. Mirrors
 * DragX's own RegistrationActivity role, minus the WiFi/set-home first-run
 * prompts (not applicable to a phone app) and the test-bypass gesture (an
 * owner-only DragX feature not ported here yet).
 */
public class RegistrationActivity extends Activity {

    private final Handler uiHandler = new Handler(Looper.getMainLooper());

    private String bluetoothAddress;
    private String deviceName;
    private boolean toCatalog;
    private LinearLayout root;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        UiTheme.apply(this);
        setTitle("Aprovação da máquina");
        bluetoothAddress = getIntent().getStringExtra("bluetoothAddress");
        deviceName = getIntent().getStringExtra("deviceName");
        toCatalog = getIntent().getBooleanExtra("toCatalog", false);

        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(UiTheme.BACKGROUND);
        int pad = dp(16);
        root.setPadding(pad, pad, pad, pad);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);

        showLoading();
        checkStatus();
    }

    private void checkStatus() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                final String status = DeviaRegistrationGate.fetchStatus(bluetoothAddress);
                uiHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        onStatusResult(status);
                    }
                });
            }
        }, "DeviaRegCheck").start();
    }

    private void onStatusResult(String status) {
        if (status == null) {
            // Network failure -- fall back to last known local state rather
            // than assuming the worst (same offline-tolerance rule as
            // DragX's RegistrationGate).
            String cached = DeviaRegistrationGate.readStatus(this);
            if ("approved".equals(cached)) {
                proceedToNextScreen();
                return;
            }
            showOfflineRetry();
            return;
        }
        if (DeviaRegistrationGate.NOT_REGISTERED.equals(status)) {
            showRegistrationForm();
            return;
        }
        DeviaRegistrationGate.writeStatus(this, status);
        DeviaRegistrationGate.startPolling(getApplicationContext(), bluetoothAddress);
        if ("approved".equals(status)) {
            proceedToNextScreen();
        } else {
            showWaiting(status);
        }
    }

    private void proceedToNextScreen() {
        Class<?> target = toCatalog ? BrandActivity.class : CutActivity.class;
        startActivity(new Intent(this, target));
        finish();
    }

    private void showLoading() {
        root.removeAllViews();
        TextView tv = new TextView(this);
        tv.setText("Verificando aprovacao da maquina...");
        root.addView(tv);
    }

    private void showOfflineRetry() {
        root.removeAllViews();
        TextView tv = new TextView(this);
        tv.setText("Sem conexao com o painel. Verifique a internet do celular e tente de novo.");
        root.addView(tv);
        Button retry = new Button(this);
        retry.setText("Tentar novamente");
        retry.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showLoading();
                checkStatus();
            }
        });
        root.addView(retry, buttonParams());
    }

    private void showWaiting(String status) {
        root.removeAllViews();
        TextView tv = new TextView(this);
        String label = "blocked".equals(status)
                ? "Esta maquina foi bloqueada. Fale com o suporte."
                : "Cadastro enviado. Aguardando aprovacao -- isso pode levar um tempo.";
        tv.setText(label);
        root.addView(tv);
        Button refresh = new Button(this);
        refresh.setText("Verificar de novo");
        refresh.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showLoading();
                checkStatus();
            }
        });
        root.addView(refresh, buttonParams());
    }

    private void showRegistrationForm() {
        root.removeAllViews();

        TextView tv = new TextView(this);
        tv.setText("Maquina nova (" + (deviceName != null ? deviceName : bluetoothAddress)
                + "). Preencha os dados para pedir aprovacao:");
        root.addView(tv);

        final EditText company = labeledField("Empresa");
        final EditText contact = labeledField("Nome do contato");
        final EditText phone = labeledField("Telefone");
        final EditText email = labeledField("Email");
        email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);

        Button submit = new Button(this);
        submit.setText("Enviar cadastro");
        submit.setBackgroundColor(UiTheme.PRIMARY);
        submit.setTextColor(Color.WHITE);
        submit.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                submitRegistration(
                        company.getText().toString().trim(),
                        contact.getText().toString().trim(),
                        phone.getText().toString().trim(),
                        email.getText().toString().trim());
            }
        });
        root.addView(submit, buttonParams());
    }

    private EditText labeledField(String label) {
        TextView lbl = new TextView(this);
        lbl.setText(label);
        lbl.setPadding(0, dp(8), 0, 0);
        root.addView(lbl);
        EditText field = new EditText(this);
        root.addView(field);
        return field;
    }

    private void submitRegistration(final String company, final String contact, final String phone, final String email) {
        if (company.isEmpty() || contact.isEmpty() || phone.isEmpty() || email.isEmpty()) {
            Toast.makeText(this, "Preencha todos os campos", Toast.LENGTH_SHORT).show();
            return;
        }
        showLoading();
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean ok = DeviaRegistrationGate.submitRegistration(
                        bluetoothAddress, deviceName, phone, company, email, contact);
                uiHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        if (ok) {
                            DeviaRegistrationGate.writeStatus(RegistrationActivity.this, "pending");
                            DeviaRegistrationGate.startPolling(getApplicationContext(), bluetoothAddress);
                            showWaiting("pending");
                        } else {
                            Toast.makeText(RegistrationActivity.this,
                                    "Falha ao enviar cadastro. Tente novamente.", Toast.LENGTH_LONG).show();
                            showRegistrationForm();
                        }
                    }
                });
            }
        }, "DeviaRegSubmit").start();
    }

    private LinearLayout.LayoutParams buttonParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        params.topMargin = dp(16);
        return params;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
