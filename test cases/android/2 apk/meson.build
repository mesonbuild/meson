project('android apk', 'java',
  meson_version: '>= 1.11'
)

android = import('android')

android.generate_apk('AndroidManifest.xml', 'com/mesonbuild/android/apk/MesonActivity.java',
  app_id: 'com.mesonbuild.android.apk',
  target_sdk: 36,
  min_sdk: 31,
  resources: [
    'res/drawable/ic_meson.xml',
    'res/drawable/img_meson.xml',
    'res/layout/meson_activity.xml',
    'res/mipmap-anydpi/ic_launcher_round.xml',
    'res/mipmap-anydpi/ic_launcher.xml',
    'res/values/strings.xml',
    'res/values/themes.xml'
  ]
)
