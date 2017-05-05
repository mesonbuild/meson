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
