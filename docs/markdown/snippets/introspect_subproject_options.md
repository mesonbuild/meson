## Per-subproject options are included in buildoptions introspection

`meson introspect --buildoptions` and `meson-info/intro-buildoptions.json`
now contain rows for per-subproject options in configured build
directories: non-yielding builtin options get one row per subproject
(e.g. `sub:warning_level`), and options with a per-subproject value set
(e.g. via `-Dsub:c_args=...`) are reported with the value in effect for
that subproject.
