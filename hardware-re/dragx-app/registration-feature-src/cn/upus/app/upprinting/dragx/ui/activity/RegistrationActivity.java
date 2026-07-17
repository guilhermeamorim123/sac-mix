package cn.upus.app.upprinting.dragx.ui.activity;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class RegistrationActivity extends Activity {
    private static final String PANEL_BASE_URL = "https://dragx-fleet-panel.onrender.com";
    // Substituted for the real value at build time -- see
    // RegistrationGate's identical constant for the full explanation.
    private static final String API_KEY = "__CHECKIN_API_KEY__";

    private View formLayout;
    private View waitingLayout;
    private TextView waitingMessage;
    private EditText phoneField;
    private EditText companyField;
    private EditText emailField;
    private EditText contactField;
    private Button submitButton;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(getResources().getIdentifier("activity_registration", "layout", getPackageName()));

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
    }

    @Override
    protected void onResume() {
        super.onResume();
        renderForCurrentStatus();
        RegistrationGate.startPolling(getApplicationContext());
    }

    private int id(String name) {
        return getResources().getIdentifier(name, "id", getPackageName());
    }

    private void renderForCurrentStatus() {
        String status = RegistrationGate.readStatus(this);
        if ("pending".equals(status)) {
            formLayout.setVisibility(View.GONE);
            waitingLayout.setVisibility(View.VISIBLE);
            waitingMessage.setText("Cadastro enviado. Aguardando aprovação...");
        } else if ("blocked".equals(status)) {
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
        } else {
            formLayout.setVisibility(View.VISIBLE);
            waitingLayout.setVisibility(View.GONE);
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
                final boolean success = doSubmit(phone, company, email, contact);
                mainHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        submitButton.setEnabled(true);
                        if (success) {
                            RegistrationGate.writeStatus(RegistrationActivity.this, "pending");
                            renderForCurrentStatus();
                        } else {
                            // Keep the four fields filled in -- design's
                            // Error handling section: don't silently lose
                            // what the customer typed.
                            Toast.makeText(RegistrationActivity.this,
                                    "Não foi possível enviar o cadastro. Verifique a internet e tente novamente.",
                                    Toast.LENGTH_LONG).show();
                        }
                    }
                });
            }
        }).start();
    }

    private boolean doSubmit(String phone, String company, String email, String contact) {
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
}
