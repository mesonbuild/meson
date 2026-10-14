## Cargo dev-dependencies and build-time crates

The Cargo workspace object can now build development and build-time
dependencies.

For development dependencies, there is a new `rust.dev_dependencies` option.
When it is set, the `[dev-dependencies]` of Cargo packages are resolved, so
that `package.dependencies(dev_dependencies: true)` can be used to build the
tests of a Cargo package.  The option can be set separately for each
subproject, and it applies to the Cargo packages that are built as part of that
subproject, whether with `rust.workspace()` or as a Cargo subproject.

The option defaults to `workspace`, which resolves `[dev-dependencies]` for
the members of Cargo workspaces that a Meson project builds directly, but
not for crates that are built as dependencies.
For the toplevel project, this matches the behavior of `cargo`, which
resolves `[dev-dependencies]` only for the members of the workspace being
built and not for their dependencies.  The option can also be set to `true`
or `false`.

As with `cargo test`, the features requested by dev-dependencies are unified
with the rest of the build; note however that Meson does not use separate build
artifacts for tests, unlike Cargo.

For build dependencies, the `extra_members` argument of `rust.workspace()`
now always accepts a package that is referenced in a `path` dependency,
even when the dependency is optional or is hidden behind a `[target]`
condition that is never true.  This makes it possible to declare packages
that exist only to generate code at build time:

```toml
[target.'cfg(any())'.build-dependencies]
generator = { path = "generator" }
```

Such a package is configured for the build machine, as Cargo would do for a
`[build-dependencies]` entry, and can be built with:

```
cargo = rust.workspace(extra_members: ['generator'])
gen_pkg = cargo.package('generator', native: true)
gen = gen_pkg.executable()
```
