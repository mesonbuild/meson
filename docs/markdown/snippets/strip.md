## `meson install --strip`

It is now possible to strip targets using `meson install --strip` even if
`-Dstrip=true` option was not set during configuration. This allows doing
stripped and not stripped installations without reconfiguring the build.
