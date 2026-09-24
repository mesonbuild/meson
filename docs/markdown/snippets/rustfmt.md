## Meson can run "rustfmt" on Rust projects

Meson now defines `rustfmt` and `rustfmt-check` targets if the project
uses the Rust programming language.  The target runs rustfmt on all Rust
sources, using the `rustfmt` program from the same Rust toolchain as the
`rustc` compiler.
