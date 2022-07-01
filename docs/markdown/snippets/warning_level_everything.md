## `warning-level=everything` option

The new `everything` value for the built-in `warning_level` enables roughly all applicable compiler warnings.
For clang and MSVC, this simply enables `-Weverything` or `/Wall`, respectively.
For GCC, meson enables warnings approximately equivalent to `-Weverything` from clang.
