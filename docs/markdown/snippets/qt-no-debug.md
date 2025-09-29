## meson now defines `QT_DEBUG` or `QT_NO_DEBUG` depending on build type

When using the `qt` meson modules, the `QT_DEBUG` or `QT_NO_DEBUG` preprocessor macro is now set depending on the value of the `debug` built-in meson option.
This mimicks the behavior of `qmake`, and is expected by the `<QtGlobal>` header.
