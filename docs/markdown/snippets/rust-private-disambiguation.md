## Rust compiler-private library disambiguation

When building a Rust target with Rust library dependencies, an
`--extern` argument is now specified to avoid ambiguity between the
dependency library, and any crates of the same name in `rustc`'s
private sysroot.
