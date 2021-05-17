---
title: Rust
short-description: Working with Rust in Meson
---

# Using Rust with Meson

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

You can use a [[structured_source]] for this. Structured sources are a dictionary
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
    structured_sources(
        'main.rs',
        {
            'foo' : ['bar.rs', 'foo/lib.rs', generated_rs],
            'foo/bar' : [...],
            'other' : [...],
        }
    )
)
```
