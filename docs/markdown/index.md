---
render-subpages: false
...

# The Meson Build system

## Overview

Meson is an open source build system meant to be both extremely fast,
and, even more importantly, as user friendly as possible.

The main design point of Meson is that every moment a developer spends
writing or debugging build definitions is a second wasted. So is every
second spent waiting for the build system to actually start compiling
code.

## Features

*   multiplatform support for Linux, macOS, Windows, GCC, Clang, Visual Studio and others
*   supported languages include C, C++, D, Fortran, Java, Rust
*   build definitions in a very readable and user friendly non-Turing complete DSL
*   cross compilation for many operating systems as well as bare metal
*   optimized for extremely fast full and incremental builds without sacrificing correctness
*   built-in multiplatform dependency provider that works together with distro packages
*   fun!

## A full manual

The documentation on this site is freely available for all. However
there is also a full separate manual available for purchase [on this
web page](https://meson-manual.com/).

## Community

There are two main methods of connecting with other Meson
developers. The first one is the mailing list, which is hosted at
[Google Groups](https://groups.google.com/forum/#!forum/mesonbuild).

The second way is via IRC. The channel to use is `#mesonbuild` at
[Freenode](https://freenode.net/).

### [Projects using Meson](Users.md)

Many projects out there are using Meson and their communities are also
a great resource for learning about what (and what not too!) do when
trying to convert to using Meson.

[A short list of Meson users can be found here](Users.md)
but there are many more. We would love to hear about your success
stories too and how things could be improved too!

## Development

All development on Meson is done on the [GitHub
project](https://github.com/mesonbuild/meson). Instructions for
contributing can be found on the [contribution page](Contributing.md).


You do not need to sign a CLA to contribute to Meson.
