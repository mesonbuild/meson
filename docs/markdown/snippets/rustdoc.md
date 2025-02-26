## Meson can run "rustdoc" on Rust projects

Meson now defines a `rustdoc` target if the project
uses the Rust programming language.  The target runs rustdoc on all Rust
sources, using the `rustdoc` program from the same Rust toolchain as the
`rustc` compiler.
