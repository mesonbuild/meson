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

Meson currently does not support creating a single target with Rust and non Rust
sources mixed together, therefore one must compile multiple libraries and link
them.

```meson
rust_lib = static_library(
    'rust_lib',
    sources : 'lib.rs',
    ...
)

c_lib = static_library(
    'c_lib',
    sources : 'lib.c',
    link_with : rust_lib,
)
```
This is an implementation detail of Meson, and is subject to change in the future.

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
docs](https://rust-analyzer.github.io/manual.html#non-cargo-based-projects) for
more information on how to configure that.

## Linking with standard libraries

Meson will link the Rust standard libraries (e.g. libstd) statically, unless the
target is a proc macro or dylib, or it depends on a dylib, in which case [`-C
prefer-dynamic`](https://doc.rust-lang.org/rustc/codegen-options/index.html#prefer-dynamic)
will be passed to the Rust compiler, and the standard libraries will be
dynamically linked.
