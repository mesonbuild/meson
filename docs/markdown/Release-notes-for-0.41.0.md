---
title: Release 0.41
short-description: Release notes for 0.41 (preliminary)
...

**Preliminary, 0.41.0 has not been released yet.**

# New features

Add features here as code is merged to master.

## Dependency Handler for LLVM

Native support for linking against LLVM using the `dependency` function.

## vcs_tag keyword fallback is is now optional

The `fallback` keyword in `vcs_tag` is now optional. If not given, its value
defaults to the return value of `meson.project_version()`.

## Better quoting of special characters in ninja command invocations

The ninja backend now quotes special characters that may be interpreted by
ninja itself, providing better interoperability with custom commands. This
support may not be perfect; please report any issues found with special
characters to the issue tracker.

## Support for passing arguments to Rust compiler

Targets for building rust now take a `rust_args` keyword.