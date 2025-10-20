## Set [[dependency]] and [[subproject]] build method

Subprojects can already define a build method in their `.wrap` file. It can
now also be done with [[dependency]]'s `fallback_method` and [[subproject]]'s
`method` keyword arguments. Supported values are `meson`, `cmake` and `cargo`.
It defaults to the `method` field in the wrap file if any, otherwise it defaults
to `meson`.
