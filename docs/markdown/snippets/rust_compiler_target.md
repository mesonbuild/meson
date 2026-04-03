## `compiler_target()` method in the Rust module

A `compiler_target()` method that returns the Rust target triple has been added to
the `rust` module. This method can be useful when converting build scripts
making use of Cargo's `TARGET` and `HOST` environment variables to
Meson.
