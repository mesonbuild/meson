## Mixing static and generated Rust sources

Meson now is handles mixing Rust code that is static (checked into the source
tree), and generated either with `custom_target` or `configure_file` (not
with `generator()`). It does this by copying the static sources to the build
tree and compiling in the build tree.
