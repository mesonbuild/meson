## Meson and meson configure now accept the same arguments

Previously meson required that builtin arguments (like prefix) be passed as
`--prefix` to `meson` and `-Dprefix` to `meson configure`. `meson` now accepts -D
form like `meson configure` has. `meson configure` also accepts the `--prefix`
form, like `meson` has.
