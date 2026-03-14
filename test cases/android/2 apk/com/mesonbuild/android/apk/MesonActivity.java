package com.mesonbuild.android.apk;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;

public class MesonActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT < 35)
            getWindow().setDecorFitsSystemWindows(false);

        setContentView(R.layout.meson_activity);
    }
}
