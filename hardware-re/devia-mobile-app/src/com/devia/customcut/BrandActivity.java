package com.devia.customcut;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Step 1 of the catalog browser: pick a brand. Mirrors DragX's
 * layout_activity_classify_brand.xml (search box + grid of cards) --
 * see PhoneCatalog's class comment for why this is placeholder data.
 */
public class BrandActivity extends Activity {

    private GridLayout grid;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        UiTheme.apply(this);
        setTitle("Escolha a marca");
        setContentView(buildUi());
        renderBrands(PhoneCatalog.BRANDS);
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(UiTheme.BACKGROUND);

        LinearLayout searchBar = new LinearLayout(this);
        searchBar.setOrientation(LinearLayout.HORIZONTAL);
        searchBar.setBackgroundColor(UiTheme.PRIMARY);
        int pad = dp(12);
        searchBar.setPadding(pad, pad, pad, pad);

        EditText search = new EditText(this);
        search.setHint("Buscar marca...");
        search.setSingleLine(true);
        search.setBackgroundColor(Color.WHITE);
        search.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                filterBrands(s.toString());
            }

            @Override
            public void afterTextChanged(Editable s) {
            }
        });
        searchBar.addView(search, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        root.addView(searchBar);

        grid = new GridLayout(this);
        grid.setColumnCount(2);
        int gridPad = dp(8);
        grid.setPadding(gridPad, gridPad, gridPad, gridPad);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(grid);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        return root;
    }

    private void filterBrands(String query) {
        List<PhoneCatalog.Brand> filtered = new ArrayList<>();
        String q = query.toLowerCase(Locale.getDefault()).trim();
        for (PhoneCatalog.Brand b : PhoneCatalog.BRANDS) {
            if (q.isEmpty() || b.name.toLowerCase(Locale.getDefault()).contains(q)) {
                filtered.add(b);
            }
        }
        renderBrands(filtered);
    }

    private void renderBrands(List<PhoneCatalog.Brand> brands) {
        grid.removeAllViews();
        for (final PhoneCatalog.Brand brand : brands) {
            grid.addView(buildBrandCard(brand));
        }
    }

    private View buildBrandCard(final PhoneCatalog.Brand brand) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.WHITE);
        bg.setCornerRadius(dp(10));
        card.setBackground(bg);

        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = dp(160);
        params.height = dp(130);
        params.setMargins(dp(8), dp(8), dp(8), dp(8));
        card.setLayoutParams(params);

        TextView name = new TextView(this);
        name.setText(brand.name);
        name.setTextSize(16);
        name.setGravity(Gravity.CENTER);
        name.setTextColor(UiTheme.CARD_LABEL);
        card.addView(name);

        card.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent intent = new Intent(BrandActivity.this, ModelActivity.class);
                intent.putExtra("brand", brand.name);
                startActivity(intent);
            }
        });

        return card;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
