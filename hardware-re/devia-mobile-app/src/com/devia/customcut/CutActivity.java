package com.devia.customcut;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
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
 * Custom-size cut screen. Requires an active connection already stored in
 * DeviaSession (set by ConnectActivity) -- finishes back to it if there
 * isn't one (e.g. app was killed and this screen restored directly).
 */
public class CutActivity extends Activity {

    private final Handler uiHandler = new Handler(Looper.getMainLooper());

    private final DeviaBluetoothLink.Listener screenListener = new DeviaBluetoothLink.Listener() {
        @Override
        public void onLine(String line) {
            log("<- " + line);
        }

        @Override
        public void onError(Exception e) {
            log("Erro: " + e.getMessage());
        }

        @Override
        public void onDisconnected() {
            log("Desconectado.");
        }
    };

    private EditText widthField;
    private EditText heightField;
    private EditText radiusField;
    private TextView logView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (!DeviaSession.get().isConnected()) {
            Toast.makeText(this, "Conecte a maquina primeiro", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }
        UiTheme.apply(this);
        setTitle("Corte customizado -- " + DeviaSession.get().getDeviceLabel());
        setContentView(buildUi());
    }

    @Override
    protected void onResume() {
        super.onResume();
        DeviaSession.get().setActiveListener(screenListener);
    }

    @Override
    protected void onPause() {
        super.onPause();
        DeviaSession.get().clearActiveListener(screenListener);
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(UiTheme.BACKGROUND);
        int pad = dp(16);
        root.setPadding(pad, pad, pad, pad);

        root.addView(labeled("Largura (mm)"));
        widthField = numberField();
        root.addView(widthField);

        root.addView(labeled("Altura (mm)"));
        heightField = numberField();
        root.addView(heightField);

        root.addView(labeled("Raio do canto (mm)"));
        radiusField = numberField();
        radiusField.setText("2");
        root.addView(radiusField);

        Button sendButton = new Button(this);
        sendButton.setText("Enviar corte");
        sendButton.setBackgroundColor(UiTheme.PRIMARY);
        sendButton.setTextColor(Color.WHITE);
        sendButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                onSendClicked();
            }
        });
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        btnParams.topMargin = dp(16);
        root.addView(sendButton, btnParams);

        logView = new TextView(this);
        logView.setPadding(0, dp(16), 0, 0);
        root.addView(logView);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        return scroll;
    }

    private TextView labeled(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setPadding(0, dp(8), 0, 0);
        return tv;
    }

    private EditText numberField() {
        EditText et = new EditText(this);
        et.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
        return et;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }

    private void log(final String msg) {
        uiHandler.post(new Runnable() {
            @Override
            public void run() {
                logView.append(msg + "\n");
            }
        });
    }

    private void onSendClicked() {
        float widthMm = parseFieldOrWarn(widthField, "largura");
        float heightMm = parseFieldOrWarn(heightField, "altura");
        float radiusMm = parseFieldOrWarn(radiusField, "raio");
        if (Float.isNaN(widthMm) || Float.isNaN(heightMm) || Float.isNaN(radiusMm)) {
            return;
        }

        final String command = DeviaProtocol.buildCutCommand(widthMm, heightMm, radiusMm);
        String preview = command.length() > 120 ? command.substring(0, 120) + "..." : command;

        new AlertDialog.Builder(this)
                .setTitle("Confirmar corte")
                .setMessage("Isto vai mandar um comando de corte real para a maquina.\n\n"
                        + widthMm + "x" + heightMm + "mm, raio " + radiusMm + "mm\n\n"
                        + "Prevista (" + command.length() + " bytes):\n" + preview)
                .setPositiveButton("Enviar", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        doSendCut(command);
                    }
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    private float parseFieldOrWarn(EditText field, String label) {
        try {
            return Float.parseFloat(field.getText().toString().trim());
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Preencha " + label + " com um numero valido", Toast.LENGTH_SHORT).show();
            return Float.NaN;
        }
    }

    private void doSendCut(final String command) {
        final DeviaBluetoothLink link = DeviaSession.get().getLink();
        if (link == null) {
            log("Sem conexao ativa.");
            return;
        }
        log("Enviando comando de corte (" + command.length() + " bytes)...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    link.sendCutJob(command);
                    log("Comando enviado. Aguardando PGREADY/PGOK/PGERR...");
                } catch (Exception e) {
                    log("Falha ao enviar corte: " + e.getMessage());
                }
            }
        }, "DeviaSendCut").start();
    }
}
