package com.devia.customcut;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Device picker + Bluetooth Classic RFCOMM connect + identification
 * handshake. On success, stores the live link in DeviaSession and
 * unlocks "Continuar" into CutActivity.
 */
public class ConnectActivity extends Activity {

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
            uiHandler.post(new Runnable() {
                @Override
                public void run() {
                    connectButton.setEnabled(true);
                    continueButton.setEnabled(false);
                }
            });
        }
    };

    private Spinner deviceSpinner;
    private Button connectButton;
    private Button continueButton;
    private TextView logView;
    private List<BluetoothDevice> pairedDevices = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        UiTheme.apply(this);
        setTitle("Conectar a maquina");
        setContentView(buildUi());
        populateDevices();
        if (DeviaSession.get().isConnected()) {
            log("Ja conectado a " + DeviaSession.get().getDeviceLabel());
            connectButton.setEnabled(false);
            continueButton.setEnabled(true);
        }
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

        deviceSpinner = new Spinner(this);
        root.addView(deviceSpinner);

        connectButton = new Button(this);
        connectButton.setText("Conectar");
        connectButton.setBackgroundColor(UiTheme.PRIMARY);
        connectButton.setTextColor(Color.WHITE);
        connectButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                onConnectClicked();
            }
        });
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        btnParams.topMargin = dp(8);
        root.addView(connectButton, btnParams);

        continueButton = new Button(this);
        continueButton.setText("Continuar");
        continueButton.setEnabled(false);
        continueButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                boolean toCatalog = getIntent().getBooleanExtra("toCatalog", false);
                Intent intent = new Intent(ConnectActivity.this, RegistrationActivity.class);
                intent.putExtra("bluetoothAddress", DeviaSession.get().getDeviceAddress());
                intent.putExtra("deviceName", DeviaSession.get().getDeviceNameOnly());
                intent.putExtra("toCatalog", toCatalog);
                startActivity(intent);
            }
        });
        LinearLayout.LayoutParams contParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        contParams.topMargin = dp(8);
        root.addView(continueButton, contParams);

        logView = new TextView(this);
        logView.setPadding(0, dp(16), 0, 0);
        root.addView(logView);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        return scroll;
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

    private void populateDevices() {
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter == null) {
            log("Este aparelho nao tem Bluetooth.");
            return;
        }
        if (!adapter.isEnabled()) {
            log("Bluetooth desligado -- ligue nas configuracoes e reabra o app.");
            return;
        }
        Set<BluetoothDevice> bonded = adapter.getBondedDevices();
        pairedDevices = new ArrayList<>(bonded);
        List<String> names = new ArrayList<>();
        for (BluetoothDevice d : pairedDevices) {
            names.add(d.getName() + " (" + d.getAddress() + ")");
        }
        ArrayAdapter<String> spinnerAdapter = new ArrayAdapter<>(
                this, android.R.layout.simple_spinner_dropdown_item, names);
        deviceSpinner.setAdapter(spinnerAdapter);
        if (names.isEmpty()) {
            log("Nenhum dispositivo pareado. Pareie a maquina em Configuracoes > Bluetooth antes de abrir o app.");
        }
    }

    private void onConnectClicked() {
        int idx = deviceSpinner.getSelectedItemPosition();
        if (idx < 0 || idx >= pairedDevices.size()) {
            Toast.makeText(this, "Escolha um dispositivo pareado primeiro", Toast.LENGTH_SHORT).show();
            return;
        }
        final BluetoothDevice device = pairedDevices.get(idx);
        connectButton.setEnabled(false);
        log("Conectando a " + device.getName() + "...");

        new Thread(new Runnable() {
            @Override
            public void run() {
                final DeviaBluetoothLink link = new DeviaBluetoothLink(device, DeviaSession.get());
                try {
                    link.connect();
                    DeviaSession.get().setLink(link, device);
                    log("Conectado. Rodando handshake de identificacao...");
                    runHandshake(link);
                    uiHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            continueButton.setEnabled(true);
                        }
                    });
                } catch (Exception e) {
                    log("Falha ao conectar: " + e.getMessage());
                    uiHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            connectButton.setEnabled(true);
                        }
                    });
                }
            }
        }, "DeviaConnect").start();
    }

    /** Sends the read-only identification commands already confirmed live this session. */
    private void runHandshake(DeviaBluetoothLink link) {
        String[] idCommands = {";RHVER;", ";RPID;", ";RPGHEAD;", ";RSVER;", ";RMODE;"};
        for (String cmd : idCommands) {
            try {
                log("-> " + cmd);
                link.sendCommand(cmd);
                Thread.sleep(200);
            } catch (Exception e) {
                log("Erro no handshake: " + e.getMessage());
                return;
            }
        }
    }
}
