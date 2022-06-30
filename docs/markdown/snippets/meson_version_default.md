## `project(meson_version : )` now defaults to `>= 0.37.0`

This change ensures that new feature and deprecation warnings are emitted, even when a meson_version is not set. 0.37 is from April of 2017, hopefully no one is depending on features from an older version.
