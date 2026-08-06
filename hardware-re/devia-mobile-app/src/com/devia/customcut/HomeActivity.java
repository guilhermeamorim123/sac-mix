package com.devia.customcut;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * Launcher screen. Structurally mirrors DragX's home screen (see
 * res/layout/layout_activity_main.xml + item_main_type_grid.xml in the
 * DragX project): a colored top bar, then a grid of white rounded cards,
 * one per feature. DragX's own icon/photo assets are NOT reused here
 * (those are the vendor's compiled art, not something to copy into an
 * unrelated app) -- only the layout PATTERN (top bar + card grid) and the
 * real on-screen brand color (#1faa4a green, confirmed from DragX's own
 * colors.xml) are replicated.
 *
 * Only one feature card exists for now (custom-size cut) -- catalog,
 * history and balance are deferred, see project memory.
 */
public class HomeActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        UiTheme.apply(this);
        if (getActionBar() != null) {
            getActionBar().hide();
        }
        setContentView(buildUi());
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(UiTheme.BACKGROUND);

        root.addView(buildTopBar());

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(2);
        int gridPad = dp(8);
        grid.setPadding(gridPad, gridPad, gridPad, gridPad);
        grid.addView(buildFeatureCard("Corte\nCustomizado", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(HomeActivity.this, ConnectActivity.class));
            }
        }));
        grid.addView(buildFeatureCard("Catalogo\nde Modelos", new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent intent = new Intent(HomeActivity.this, ConnectActivity.class);
                intent.putExtra("toCatalog", true);
                startActivity(intent);
            }
        }));
        root.addView(grid);

        return root;
    }

    private View buildTopBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setBackgroundColor(UiTheme.PRIMARY);
        int vPad = dp(14);
        int hPad = dp(16);
        bar.setPadding(hPad, vPad, hPad, vPad);

        TextView title = new TextView(this);
        title.setText("DRAGX");
        title.setTextSize(18);
        title.setTypeface(null, Typeface.BOLD);
        title.setTextColor(Color.WHITE);
        bar.addView(title);

        return bar;
    }

    private View buildFeatureCard(String label, View.OnClickListener onClick) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER);
        card.setBackground(cardBackground(Color.WHITE));
        card.setOnClickListener(onClick);

        GridLayout.LayoutParams params = cardLayoutParams();
        card.setLayoutParams(params);

        TextView label1 = new TextView(this);
        label1.setText(label);
        label1.setTextSize(16);
        label1.setGravity(Gravity.CENTER);
        label1.setTextColor(UiTheme.CARD_LABEL);
        card.addView(label1);

        return card;
    }

    private View buildComingSoonCard(String label) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER);
        card.setBackground(cardBackground(Color.parseColor("#e8e8e8")));
        card.setLayoutParams(cardLayoutParams());

        TextView label1 = new TextView(this);
        label1.setText(label);
        label1.setTextSize(16);
        label1.setGravity(Gravity.CENTER);
        label1.setTextColor(Color.parseColor("#999999"));
        card.addView(label1);

        TextView soon = new TextView(this);
        soon.setText("em breve");
        soon.setTextSize(12);
        soon.setGravity(Gravity.CENTER);
        soon.setTextColor(Color.parseColor("#aaaaaa"));
        soon.setPadding(0, dp(6), 0, 0);
        card.addView(soon);

        return card;
    }

    private GridLayout.LayoutParams cardLayoutParams() {
        GridLayout.LayoutParams params = new GridLayout.LayoutParams();
        params.width = dp(160);
        params.height = dp(160);
        params.setMargins(dp(8), dp(8), dp(8), dp(8));
        return params;
    }

    private GradientDrawable cardBackground(int color) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(10));
        return drawable;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
