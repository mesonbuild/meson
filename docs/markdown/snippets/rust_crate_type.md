## Deprecated `rust_crate_type` and replaced by `rust_abi`

The new `rust_abi` keyword argument is accepted by [[shared_library]],
[[static_library]], [[library]] and [[shared_module]] functions. It can be either
`'rust'` (the default) or `'c'` strings.

`rust_crate_type` is now deprecated because Meson already knows if it's a shared
or static library, user only need to specify the ABI (Rust or C).

`proc_macro` crates are now handled by the [`rust.proc_macro()`](Rust-module.md#proc_macro)
method.
