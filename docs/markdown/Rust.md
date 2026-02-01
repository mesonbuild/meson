---
title: Rust
short-description: Working with Rust in Meson
...

# Using Rust with Meson

## Avoid using `extern crate`

Meson can't track dependency information for crates linked by rustc as
a result of `extern crate` statements in Rust source code.  If your
crate dependencies are properly expressed in Meson, there should be no
need for `extern crate` statements in your Rust code, as long as you use the
Rust 2018 edition or later. This means adding `rust_std=2018` (or later) to the
`project(default_options)` argument.

An example of the problems with `extern crate` is that if you delete a
crate from a Meson build file, other crates that depend on that crate
using `extern crate` might continue linking with the leftover rlib of
the deleted crate rather than failing to build, until the build
directory is cleaned.

This limitation could be resolved in future with rustc improvements,
for example if the [`-Z
binary-dep-depinfo`](https://github.com/rust-lang/rust/issues/63012)
feature is stabilized.

## Mixing Rust and non-Rust sources

*(Since 1.9.0)* Rust supports mixed targets, but only supports using
`rustc` as the linker for such targets. If you need to use a non-Rust
linker, or support Meson < 1.9.0, see below.

Until Meson 1.9.0, Meson did not support creating a single target with
Rust and non Rust sources mixed together. One had to compile a separate
Rust `static_library` or `shared_library`, and link it into the C build
target (e.g., a library or an executable).

```meson
rust_lib = static_library(
    'rust_lib',
    sources : 'lib.rs',
    rust_abi: 'c',
    ...
)

c_lib = static_library(
    'c_lib',
    sources : 'lib.c',
    link_with : rust_lib,
)
```

## Mixing Generated and Static sources

*Note* This feature was added in 0.62

You can use a [[@structured_src]] for this. Structured sources are a dictionary
mapping a string of the directory, to a source or list of sources.
When using a structured source all inputs *must* be listed, as Meson may copy
the sources from the source tree to the build tree.

Structured inputs are generally not needed when not using generated sources.

As an implementation detail, Meson will attempt to determine if it needs to copy
files at configure time and will skip copying if it can. Copying is done at
build time (when necessary), to avoid reconfiguring when sources change.

```meson
executable(
    'rust_exe',
    [[#structured_sources]](
        'main.rs',
        {
            'foo' : ['bar.rs', 'foo/lib.rs', generated_rs],
            'foo/bar' : [...],
            'other' : [...],
        }
    )
)
```

## Use with rust-analyzer

*Since 0.64.0.*

Meson will generate a `rust-project.json` file in the root of the build
directory if there are any rust targets in the project. Most IDEs will need to
be configured to use the file as it's not in the source root (Meson does not
write files into the source directory). [See the upstream
docs](https://rust-analyzer.github.io/book/non_cargo_based_projects.html) for
more information on how to configure that.

## Linking with standard libraries

Meson will link the Rust standard libraries (e.g. libstd) statically, unless the
target is a proc macro or dylib, or it depends on a dylib, in which case [`-C
prefer-dynamic`](https://doc.rust-lang.org/rustc/codegen-options/index.html#prefer-dynamic)
will be passed to the Rust compiler, and the standard libraries will be
dynamically linked.

## Multiple targets for the same crate name

For library targets that have `rust_abi: 'rust'`, the crate name is derived from the
target name.  First, dashes, spaces and dots are replaced with underscores.  Second,
*since 1.10.0* anything after the first `+` is dropped.  This allows creating multiple
targets for the same crate name, for example when the same crate is built multiple
times with different features, or for both the build and the host machine.

## Compiler vs. linker arguments for Rust

While `rustc` integrates the compiler and linker phase, it is useful
to pass linker arguments to it via the `-Clink-arg=` command line
option.

*Since 1.11.0* `add_project_link_arguments()`,
`add_global_link_arguments()`, the `link_args` keyword argument wrap the
arguments with `-Clink-arg=` before passing them to the Rust compiler.
Furthermore, these arguments are only included when creating binary or
shared library crates.  Likewise, methods such as `has_link_argument()`
wrap the arguments being tested with `-Clink-arg=`.

## Cargo interaction

*Since 1.11.0*

In most cases, a Rust program will use Cargo to download crates.  Meson is able
to build Rust library crates based on a `Cargo.toml` file; each external crate
corresponds to a subproject.  Rust module's ` that do not need a `build.rs` file
need no intervention, whereas if a `build.rs` file is present it needs to be
converted manually to Meson code.

To enable automatic configuration of Cargo dependencies, your project must
have `Cargo.toml` and `Cargo.lock` files in the root source directory;
this enables proper feature resolution across crates.  You can then
create a workspace object using the Rust module, and retrieve specific
packages from the workspace:

```meson
rust = import('rust')
cargo_ws = rustmod.workspace()
anyhow_dep = ws.subproject('anyhow').dependency()
```

The workspace object also enables configuration of Cargo features, for example
from Meson options:

```meson
cargo_ws = rustmod.workspace(
    features: ['feature1', 'feature2'])
```

### Limitations

All your own crates must be built using the usual Meson functions such as
[[static_library]] or [[executable]].  In the future, workspace object
functionality will be extended to help building rustc command lines
based on features, dependency names, and so on.
