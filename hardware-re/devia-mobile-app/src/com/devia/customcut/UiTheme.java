package com.devia.customcut;

import android.app.ActionBar;
import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.view.Window;

/**
 * Shared visual identity: same green palette DragX actually uses on screen
 * (res/values/colors.xml in the DragX project: "theme"/"main_bg_bar" =
 * #1faa4a -- NOT the unused colorPrimary indigo boilerplate left over from
 * the original Android Studio template, which never appears in any real
 * DragX screen). Applied programmatically since this app has no compiled
 * resources/themes.
 */
final class UiTheme {
    static final int PRIMARY = Color.parseColor("#1faa4a");
    static final int PRIMARY_DARK = Color.parseColor("#158038");
    static final int BACKGROUND = Color.parseColor("#f5f5f7");
    static final int CARD_LABEL = Color.parseColor("#333333");

    private UiTheme() {
    }

    static void apply(Activity activity) {
        ActionBar bar = activity.getActionBar();
        if (bar != null) {
            bar.setBackgroundDrawable(new ColorDrawable(PRIMARY));
        }
        Window window = activity.getWindow();
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            window.setStatusBarColor(PRIMARY_DARK);
        }
    }
}
