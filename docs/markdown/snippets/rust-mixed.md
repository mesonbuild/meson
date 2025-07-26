## Rust and non-Rust sources in the same target

Meson now supports creating a single target with Rust and non Rust
sources mixed together.  In this case, if specified, `link_language`
must be set to `rust`.
