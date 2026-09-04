## New `b_freestanding` base option

The new `b_freestanding` base option tells supported compilers that targets do
not assume a hosted standard library. GCC-compatible C-family compilers receive
`-ffreestanding`, while clang-cl receives `/clang:-ffreestanding`.

For Rust targets, the option declares that the crate uses `#![no_std]`. Meson
uses this information when determining the native libraries required by Rust
static libraries. Meson does not add the crate attribute itself.
