# New "clippy-json" Ninja Target For rust-analyzer

A new `clippy-json` ninja target will now be generated for rust projects.

rust-analyzer supports non-cargo based projects so long as you provide it with a `rust-project.json` file and a custom "check command" to provide compiler errors.

Meson already for some time has generated a `rust-project.json` file for rust-analyzer, but had no way to hook up its rustc/clippy output to rust-analyzer.

To use the new feature, you want to override the rust-analyzer check command as shown [here](https://rust-analyzer.github.io/book/non_cargo_based_projects.html), and set it to `ninja clippy-json -C build` or something to the same effect.
