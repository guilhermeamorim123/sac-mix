package com.devia.customcut;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;

import java.util.List;

/**
 * Step 2 of the catalog browser: pick a model within the chosen brand.
 * Mirrors DragX's layout_activity_classify_model.xml (search + list).
 * Selecting a model does NOT pre-fill any cut dimensions -- see
 * PhoneCatalog's class comment. It only carries the brand/model name
 * forward for a friendlier CutActivity title.
 */
public class ModelActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        UiTheme.apply(this);
        final String brandName = getIntent().getStringExtra("brand");
        setTitle(brandName != null ? brandName : "Modelos");
        setContentView(buildUi(brandName));
    }

    private View buildUi(String brandName) {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(UiTheme.BACKGROUND);

        TextView warning = new TextView(this);
        warning.setText("Catalogo ainda sem medidas reais cadastradas. "
                + "Ao escolher um modelo, preencha a largura/altura/raio manualmente na proxima tela.");
        warning.setTextColor(Color.parseColor("#7a5b00"));
        warning.setBackgroundColor(Color.parseColor("#fff3cd"));
        int pad = dp(12);
        warning.setPadding(pad, pad, pad, pad);
        root.addView(warning);

        List<String> models = findModels(brandName);
        ListView listView = new ListView(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                this, android.R.layout.simple_list_item_1, models);
        listView.setAdapter(adapter);
        listView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                startActivity(new Intent(ModelActivity.this, CutActivity.class));
            }
        });
        root.addView(listView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        return root;
    }

    private List<String> findModels(String brandName) {
        for (PhoneCatalog.Brand b : PhoneCatalog.BRANDS) {
            if (b.name.equals(brandName)) {
                return b.models;
            }
        }
        return java.util.Collections.emptyList();
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
