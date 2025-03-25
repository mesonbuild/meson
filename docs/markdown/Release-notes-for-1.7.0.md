---
title: Release 1.7.0
short-description: Release notes for 1.7.0
...

# New features

Meson 1.7.0 was released on 26 January 2025

## Call for testing for next release

At the beginning of next cycle we aim to merge the [option refactor
branch](https://github.com/mesonbuild/meson/pull/13441). This is a
_huge_ change that will touch pretty much all code.

The main change it brings is that you can override any builtin option
value for any subproject (even the top one) entirely from the command
line. This means that you can, for example, enable optimizations on
all subprojects but not on the top level project.

We have done extensive testing and all our tests currently
pass. However it is expected that this will break some workflows. So
please test the branch when it lands and report issues. We want to fix
all regressions as soon as possible, preferably far before the next rc
release.

## New custom dependency for atomic

```
dependency('atomic')
```

checks for the availability of the atomic operation library. First, it looks
for the atomic library. If that is not found, then it will try to use what is
provided by the libc.

## `--cap-lints allow` used for Cargo subprojects

Similar to Cargo itself, all downloaded Cargo subprojects automatically
add the `--cap-lints allow` compiler argument, thus hiding any warnings
from the compiler.

Related to this, `warning_level=0` now translates into `--cap-lints allow`
for Rust targets instead of `-A warnings`.

## Cargo features are resolved globally

When configuring a Cargo dependency, Meson will now resolve its complete
dependency tree and feature set before generating the subproject AST.
This solves many cases of Cargo subprojects being configured with missing
features that the main project had to enable by hand using e.g.
`default_options: ['foo-rs:feature-default=true']`.

Note that there could still be issues in the case there are multiple Cargo
entry points. That happens if the main Meson project makes multiple `dependency()`
calls for different Cargo crates that have common dependencies.

Breaks: This change removes per feature Meson options that were previously
possible to set as shown above or from command line `-Dfoo-rs:feature-foo=true`.

## Meson can run "clippy" on Rust projects

Meson now defines a `clippy` target if the project uses the Rust programming
language.  The target runs clippy on all Rust sources, using the `clippy-driver`
program from the same Rust toolchain as the `rustc` compiler.

Using `clippy-driver` as the Rust compiler will now emit a warning, as it
is not meant to be a general-purpose compiler front-end.

## Devenv support in external project module

The [external project module](External-Project-module.md) now setups `PATH` and
`LD_LIBRARY_PATH` to be able to run programs.

`@BINDIR@` is now substitued in arguments and `'--bindir=@PREFIX@/@BINDIR@'`
default argument have been added.

## Fixed `sizeof` and `find_library` methods for Fortran compilers

The implementation of the `.sizeof()` method has been fixed for Fortran
compilers (it was previously broken since it would try to compile a C code
snippet). Note that this functionality requires Fortran 2008 support.

Incidentally this also fixes the `.find_library()` method for Fortran compilers
when the `prefer_static` built-in option is set to true.

## format command now accept stdin argument

You can now use `-` argument for `meson format` to read input from stdin
instead of reading it from a file.

## "machine" entry in target introspection data

The JSON data returned by `meson introspect --targets` now has a `machine`
entry in each `target_sources` block.  The new entry can be one of `build`
or `host` for compiler-built targets, or absent for `custom_target` targets.

## Add new language Linear Asm

TI C6000 compiler supports a dialect of TI asm, so we add a new language for it.

## Control the number of child processes with an environment variable

Previously, `meson test` checked the `MESON_TESTTHREADS` variable to control
the amount of parallel jobs to run; this was useful when `meson test` is
invoked through `ninja test` for example.  With this version, a new variable
`MESON_NUM_PROCESSES` is supported with a broader scope: in addition to
`meson test`, it is also used by the `external_project` module and by
Ninja targets that invoke `clang-tidy`, `clang-format` and `clippy`.

## Support for Rust 2024

Meson can now request the compiler to use the 2024 edition of Rust.  Use
`rust_std=2024` to activate it.  Rust 2024 requires the 1.85.0 version
(or newer) of the compiler.

## Support TASKING VX-Toolset

Meson now supports the TASKING VX-Toolset compiler family for the Tricore cpu family.

## Test targets no longer built by default

`meson test` and the `ninja all` rule have been reworked to no longer force
unnecessary rebuilds.

`meson test` was invoking `ninja all` due to a bug if the chosen set of tests
had no build dependencies. The behavior is now the same as when tests do have
build dependencies, i.e. to only build the actual set of targets that are used
by the test. This change could cause failures when upgrading to Meson 1.7.0, if
the dependencies are not specified correctly in meson.build. Using `ninja test`
has always been guaranteed to "do the right thing" and rebuild `all` as well;
this continues to work.

`ninja all` does not rebuild all tests anymore; it should be noted that this
change means test programs are no longer guaranteed to have been built,
depending on whether those test programs were *also* defined to build by
default / marked as installable. This avoids building test-only binaries as
part of installing the project (`ninja && ninja install`), which is unnecessary
and has no use case.

Some users might have been relying on the "all" target building test
dependencies in combination with `meson test --no-rebuild` in order to skip
calling out to ninja when running tests. This might break with this change
because, when given `--no-rebuild`, Meson provides no guarantee that test
dependencies are present and up to date. The recommended workflow is to use
either `ninja test` or `ninja && meson test` but, if you wish to build test
programs and dependencies in a separate stage, you can use for example `ninja
all meson-test-prereq meson-benchmark-prereq` before `meson test --no-rebuild`.
These prereq targets have been available since meson 0.63.0.

## Install vcs_tag() output

[[vcs_tag]] now has `install`, `install_dir`, `install_tag` and `install_mode`
keyword arguments to install the generated file.

