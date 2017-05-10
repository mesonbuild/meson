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

## Pkgconfig support for custom variables

The Pkgconfig module object can add arbitrary variables to the generated .pc
file with the new `variables` keyword:
```meson
pkg.generate(libraries : libs,
             subdirs : h,
             version : '1.0',
             name : 'libsimple',
             filebase : 'simple',
             description : 'A simple demo library.',
             variables : ['datadir=${prefix}/data'])
```

## A target for creating tarballs

Creating distribution tarballs is simple:

    ninja dist

This will create a `.tar.xz` archive of the source code including
submodules without any revision control information. This command also
verifies that the resulting archive can be built, tested and
installed. This is roughly equivalent to the `distcheck` target in
other build systems. Currently this only works for projects using Git
and only with the Ninja backend.


