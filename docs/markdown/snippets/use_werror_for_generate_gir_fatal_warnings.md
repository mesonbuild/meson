## Use `werror` for `gnome.generate_gir(fatal_warnings:)`

If `fatal_warnings` is not passed to `gnome.generate_gir()`, the value of
the `werror` option is now read to determine whether to turn it on.
Explicitly passing `fatal_warnings: true` or `fatal_warnings: false`
still takes precedence over `werror`.
