## Meson now defines `QT_DEBUG` or `QT_NO_DEBUG` depending on build type

When using the `qt` Meson modules, the `QT_DEBUG` or `QT_NO_DEBUG` preprocessor macro is now set depending on the value of the `debug` built-in Meson option.
This mimics the behavior of `qmake`, and is expected by the `<QtGlobal>` header.
