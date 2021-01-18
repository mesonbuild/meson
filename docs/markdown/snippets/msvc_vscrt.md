## `b_vscrt` default is now `from_debug`, `from_buildtype`/`static_from_buildtype` replaced

`b_vscrt` options `from_buildtype` and `static_from_buildtype` replaced with `from_debug` and `static_from_debug`.

This behavior is to make debug information more consistent when building with `debug=true`.
Previously, `debugoptimized` would enable `debug` but use `/MD` or `/MT` instead of `/MDd` and `/MTd`.

Also, custom combinations of `optimization` and `debug` no longer throw meson configuration exceptions when `from_debug` and `static_form_debug` are used.

The CRT behavior can still be controlled manually.