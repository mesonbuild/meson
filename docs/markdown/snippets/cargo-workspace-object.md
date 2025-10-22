## Cargo workspace object

Meson now is able to parse the toplevel `Cargo.toml` file of the
project when the `workspace()` method of the Rust module is called.
This guarantees that features are resolved according to what is
in the `Cargo.toml` file, and in fact enables configuration of
features for the build.

The returned object also allows retrieving features and dependencies
for Cargo subprojects.

While Cargo subprojects remain experimental, the Meson project will
try to keep the workspace object reasonably backwards-compatible.
