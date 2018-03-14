## Meson now accepts -D for builtin arguments at setup time like configure time

Previously meson required that builtin arguments (like prefix) be passed as
`--prefix` to `meson` and `-Dprefix` to `meson configure`. Meson now accepts -D
form like meson configure does. `meson configure` still does not accept the
`--prefix` form.
