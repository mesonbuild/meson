## Override compilers binaries

Before calling `add_languages()`, it is now possible to override the compiler's
executable using `meson.override_find_program()` with an external program.
This is intended for example when the compiler is provided by a subproject.

Note that it is the language name (e.g. `c`) that needs to be overridden, not
the compiler program name (e.g. `gcc`).

When cross compiling and a language has been overridden, the same program will
be used as native and cross compiler, that could cause issues with languages
that expects different toolchains.

```meson
meson.override_find_program('c', find_program('my-gcc-wrapper.py'))
add_languages('c')
```
