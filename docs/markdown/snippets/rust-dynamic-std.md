## New experimental option `rust_dynamic_std`

A new option `rust_dynamic_std` can be used to link Rust programs so
that they use a dynamic library for the Rust `libstd`.

Right now, `staticlib` crates cannot be produced if `rust_dynamic_std` is
true, but this may change in the future.
