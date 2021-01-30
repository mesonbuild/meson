---
short-description: Rust language integration module
authors:
    - name: Dylan Baker
      email: dylan@pnwbakers.com
      years: [2020]
...

# Unstable Rust module

*(new in 0.57.0)*

**Note** Unstable modules make no backwards compatible API guarantees.

The rust module provides helper to integrate rust code into meson. The
goal is to make using rust in meson more pleasant, while still
remaining mesonic, this means that it attempts to make rust work more
like meson, rather than meson work more like rust.

## Functions

### test(name: string, target: library | executable, dependencies: []Dependency)

This function creates a new rust unittest target from an existing rust
based target, which may be a library or executable. It does this by
copying the sources and arguments passed to the original target and
adding the `--test` argument to the compilation, then creates a new
test target which calls that executable, using the rust test protocol.

This accepts all of the keyword arguments as the
[`test`](Reference-manual.md#test) function except `protocol`, it will set
that automatically.

Additional, test only dependencies may be passed via the dependencies
argument.
