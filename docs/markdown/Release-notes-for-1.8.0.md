---
title: Release 1.8.0
short-description: Release notes for 1.8.0
...

# New features

Meson 1.8.0 was released on 28 April 2025
## New argument `android_exe_type` for executables

Android application executables actually need to be linked
as a shared object, which is loaded from a pre-warmed JVM.
Meson projects can now specify a new argument `android_exe_type`
and set it to `application`, in order produce such a shared library
only on Android targets.

This makes it possible to use the same `meson.build` file
for both Android and non-Android systems.

## Changes to the b_sanitize option

Before 1.8 the `b_sanitize` option was a combo option, which is an enumerated
set of values. In 1.8 this was changed to a free-form array of options where
available sanitizers are not hardcoded anymore but instead verified via a
compiler check.

This solves a number of longstanding issues such as:

 - Sanitizers may be supported by a compiler, but not on a specific platform
   (OpenBSD).
 - New sanitizers are not recognized by Meson.
 - Using sanitizers in previously-unsupported combinations.

To not break backwards compatibility, calling `get_option('b_sanitize')`
continues to return the configured value as a string, with a guarantee that
`address,undefined` remains ordered.

## New C standard `c2y` (and `gnu2y`)

The `c2y` standard and its companion `gnu2y` are now supported
when using either Clang 19.0.0 or newer, or GCC 15.0.0 or newer.

## i18n module xgettext

There is a new `xgettext` function in `i18n` module that acts as a
wrapper around `xgettext`. It allows to extract strings to translate from
source files.

This function is convenient, because:
- It can find the sources files from a build target;
- It will use an intermediate file when the number of source files is too
  big to be handled directly from the command line;
- It is able to get strings to translate from the dependencies of the given
  targets.

## `version_compare` now accept multiple compare strings

Is it now possible to compare version against multiple values, to check for
a range of version for instance.

```meson
'1.5'.version_compare('>=1', '<2')
```

## Improvements to Objective-C and Objective-C++

Meson does not assume anymore that gcc/g++ always support
Objective-C and Objective-C++, and instead checks that they
can actually do a basic compile.

Furthermore, Objective-C and Objective-C++ now support the
same language standards as C and C++ respectively.

## Per project subproject options rewrite

You can now define per-subproject values for all shared configuration
options. As an example you might want to enable optimizations on only
one subproject:

    meson configure -Dnumbercruncher:optimization=3

Subproject specific values can be removed with -U

    meson configure -Unumbercruncher:optimization

This is a major change in how options are handled, and the
implementation will evolve over the next few releases of Meson. If
this change causes an error in your builds, please [report an issue on
GitHub](https://github.com/mesonbuild/meson/issues/new).

We have tried to keep backwards compatibility as much as possible, but
this may lead to some build breakage.

## `objects` added correctly to Rust executables

Any objects included in a Rust executable were previously ignored.  They
are now added correctly.

## `rust.test` now supports `link_whole`

The `test` function in the `rust` module now supports the `link_whole`
keyword argument in addition to `link_with` and `dependencies`.

## Meson can run "rustdoc" on Rust projects

Meson now defines a `rustdoc` target if the project
uses the Rust programming language.  The target runs rustdoc on all Rust
sources, using the `rustdoc` program from the same Rust toolchain as the
`rustc` compiler.

## The Wayland module is stable

The Wayland module has been tested in several projects and had the
last breaking change in Meson 0.64.0; it is now marked as stable.

## New `swift_std` compiler option

A new compiler option allows to set the language version that is passed
to swiftc (`none`, `4`, `4.2`, `5` or `6`).

## New option to execute a slice of tests

When tests take a long time to run a common strategy is to slice up the tests
into multiple sets, where each set is executed on a separate machine. You can
now use the `--slice i/n` argument for `meson test` to create `n` slices and
execute the `ith` slice.

## Valgrind now fails tests if errors are found

Valgrind does not reflect an error in its exit code by default, meaning
a test may silently pass despite memory errors. Meson now exports
`VALGRIND_OPTS` such that Valgrind will exit with status 1 to indicate
an error if `VALGRIND_OPTS` is not set in the environment.

