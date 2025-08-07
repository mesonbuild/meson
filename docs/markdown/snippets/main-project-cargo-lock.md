## Common `Cargo.lock` for all Cargo subprojects

Meson will now parse a `Cargo.lock` in the toplevel source directory,
and use it to resolve the versions of Cargo subprojects in preference
to per-subproject `Cargo.lock` files.

If you wish to experiment with Cargo subprojects, it is recommended
to use `cargo` to set up `Cargo.lock` and `Cargo.toml` files,
encompassing all Rust targets, in the toplevel source directory.
Cargo subprojects remain unstable and subject to change.
