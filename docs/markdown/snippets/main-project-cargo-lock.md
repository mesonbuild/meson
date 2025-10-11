## Common `Cargo.lock` for all Cargo subprojects

Whenever Meson finds a `Cargo.lock` file in the toplevel directory
of the project, it will use it to resolve the versions of Cargo
subprojects in preference to per-subproject `Cargo.lock` files.
Per-subproject lock files are only used if the invoking project
did not have a `Cargo.lock` file itself.

If you wish to experiment with Cargo subprojects, it is recommended
to use `cargo` to set up `Cargo.lock` and `Cargo.toml` files,
encompassing all Rust targets, in the toplevel source directory.
Cargo subprojects remain unstable and subject to change.
