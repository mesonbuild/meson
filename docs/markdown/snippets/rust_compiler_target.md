## `compiler_target()` method in the Rust module

The Rust module has a `compiler_target()` method that can be useful
when converting build scripts to Meson, because its return value
matches the value of Cargo's `TARGET` and `HOST` environment variables.
