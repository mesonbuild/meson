## Python extension modules default to C ABI for Rust

`py.extension_module()` now defaults `rust_abi` to `'c'`, so that Rust
extension modules produce a `cdylib` instead of a `dylib`.  This is the
correct crate type for Python extension modules written in Rust, and
previously had to be specified manually via `rust_crate_type: 'cdylib'`
or `rust_abi: 'c'`.
