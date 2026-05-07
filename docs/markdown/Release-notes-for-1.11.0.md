---
title: Release 1.11.0
short-description: Release notes for 1.11.0
...

# New features

Meson 1.11.0 was released on 13 April 2026
## BuildTarget(install_dir) length > 1 replaced with keywords

Build targets previously supported (with limited documentation) passing an array
of more than one element to `install_dir:` (except in some wrappers), and
would map these additional `install_dir`s to extra outputs. This was only used by
Vala, and separate explicit keyword arguments are now available that provide
the same functionality.

Code like this:
```meson
library(
  'foo',
  'foo.vala',
  install : true,
  install_dir : [true, get_option('includedir') / 'foo', true],
)
```

should now be written as the much clearer:

```meson
library(
  'foo',
  'foo.vala',
  install : true,
  install_vala_header : get_option('includedir') / 'foo',
  install_vala_vapi : true,
)
```

Note that the default is `false` for the Vala extra outputs.

## Cargo workspace object

Meson is now able to parse the toplevel `Cargo.toml` file of the
project when the `workspace()` method of the Rust module is called.
This guarantees that features are resolved according to what is
in the `Cargo.toml` file, and in fact enables configuration of
features for the build.

The returned object allows retrieving features and dependencies
for Cargo subprojects, and contains methods to build targets
declared in `Cargo.toml` files.

While Cargo subprojects remain experimental, the Meson project will
try to keep the workspace object reasonably backwards-compatible.

## Cython no longer requires explicitly enabling C or C++

This only provides these languages as an implementation detail of Cython, so
native C/C++ targets cannot be compiled.

## Deduplication of OpenMP linker arguments

Meson now deduplicates linker arguments `-fopenmp` and `-qopenmp`.

## `meson dist` now accepts `-j`/`--num-processes`

`meson dist` now supports a `-j`/`--num-processes` flag to control the number of
parallel processes used during the distribution check (compilation and testing of
the generated package).  The `MESON_NUM_PROCESSES` environment variable is also
honored, consistent with other Meson commands.

## Deprecate `should_fail` and rename it to `expected_fail`, also introduce `expected_exitcode`

In 1.11.0 `should_fail` has been renamed to `expected_fail`.

Before 1.11.0, there was no way to positively test a command/binary returning error/non-zero exit code when the used protocol was set to exitcode, so `expected_exitcode` has been introduced to achieve this. Do note that if the exitcode does not match the expected value, GNU skip and exit codes are still valid and the test result may be skip or error.

## The external_project module uses the cygpath command to convert paths

In previous versions, the external_project module on Windows used a Windows-style path (e.g., `C:/path/to/configure`) to execute the configure file, and a relative path from the drive root (e.g., `/path/to/prefix`) as the installation prefix.
However, since configure scripts are typically intended to be run in a POSIX-like environment (MSYS2, Cygwin, or GitBash), these paths were incompatible with some configure scripts.

The external_project module now uses the `cygpath` command to convert the configure command path and prefix to Unix-style paths (e.g., `/c/path/to/configure` for MSYS2 and `/cygdrive/c/path/to/configure` for Cygwin).
If the `cygpath` command is not found in the PATH, it will fall back to the previous behavior.

## install_man and install_headers: add support for install_tag kwarg

`install_man` and `install_headers` now support the `install_tag` keyword argument,
allowing selection of installed files via `meson install --tags`. Previously,
`install_man` always used the `man` tag and `install_headers` always used the
`devel` tag, with no way to override them.

## Added `link_early_args` to targets performing linking

Options passed to the linker using the `link_args` keyword argument
get placed on the command line after all objects and libraries. Some
linker options, like `-u` or `--defsym`, are only useful if placed
before objects and libraries as they control how the linker
manipulates those.

The new `link_early_args` keyword argument passes linker options which
are inserted into the command line before any objects and libraries,
allowing applications to use these kinds of linker options with Meson.

This is currently only supported when using the `ninja` backend.

## Machine files now expand `~` as the user's home directory

A new constant `~` has been added which can be used in machine files (native
and cross files) to refer to the user's home directory. This is useful for
specifying paths to SDKs and toolchains that are commonly installed into `~`,
such as Qt, the Android SDK/NDK, or user-installed frameworks on macOS:

```ini
[constants]
toolchain = ~ / 'Android/sdk/ndk/27.1.12297006/toolchains/llvm/prebuilt/linux-x86_64'

[binaries]
c = toolchain / 'bin/clang'
cpp = toolchain / 'bin/clang++'
ar = toolchain / 'bin/llvm-ar'
```

Note that `~` can be used anywhere in the machine file. In the above example,
the purpose of defining a new constant called `toolchain` is to not have to
repeat yourself when using the path multiple times.

## `meson format` file sorting is now disabled by default and uses natural sorting

The `sort_files` option to `meson format`, which sorts the arguments of
`files()` invocations, is now disabled by default.

If the `sort_files` option is enabled, `meson format` now sorts `files()`
arguments [naturally](Style-guide.md#sorting-source-paths) rather than
alphabetically.

## `-Db_lto` and `-Db_pgo` now supported for MSVC

`-Db_lto` is now supported for MSVC's `/LTCG`, as is `-Db_lto_mode=thin`
for `/LTCG:INCREMENTAL`. `-Db_pgo` is also supported, and should be used
alongside `-Db_lto=true`.

## Last major version supporting Python 3.7, 3.8, and 3.9

Python older than 3.10 is now EOL, and Meson will drop support for these
versions in the next major release, and will freely use features from 3.8, 3.9
and 3.10. Support for these versions will remain for the 1.11.x series.

## Python extension modules default to C ABI for Rust

`py.extension_module()` now defaults `rust_abi` to `'c'`, so that Rust
extension modules produce a `cdylib` instead of a `dylib`.  This is the
correct crate type for Python extension modules written in Rust, and
previously had to be specified manually via `rust_crate_type: 'cdylib'`
or `rust_abi: 'c'`.

## Meson now defines `QT_DEBUG` or `QT_NO_DEBUG` depending on build type

When using the `qt` Meson modules, the `QT_DEBUG` or `QT_NO_DEBUG` preprocessor macro is now set depending on the value of the `debug` built-in Meson option.
This mimics the behavior of `qmake`, and is expected by the `<QtGlobal>` header.

## `compiler_target()` method in the Rust module

A `compiler_target()` method that returns the Rust target triple has been added to
the `rust` module. This method can be useful when converting build scripts
making use of Cargo's `TARGET` and `HOST` environment variables to
Meson.

## Change to handling of linker arguments for Rust

Since the Rust compiler integrates the compiler and linker phase, previous
Meson versions did not obey `link_args`, `add_project_link_arguments`
or `add_global_link_arguments`.

Starting in this version, `add_project_link_arguments()`,
`add_global_link_arguments()`, and the `link_args` keyword argument are
supported for Rust.  They wrap the arguments with `-Clink-arg=` when
invoking rustc, and are only included when creating binary or shared
library crates.

Likewise, methods such as `has_link_argument()` now wrap the arguments
being tested with `-Clink-arg=`.

## XC32 support now aware of v5.00 features

XC32 features introduced in v5.00 can now be used. This includes
support for LTO auto and the C2x and CPP23 standards.

## windows.compile_resources now detects header changes with rc.exe

The `rc.exe` resource compiler neither provides *depfile* support nor
allows showing includes, as is possible with C or C++ compilers.
Therefore, changes to files included by the `.rc` file did not trigger
recompilation of the resource file.

A workaround was added to Meson by calling the preprocessor on the
`.rc` file to display the included headers and allow ninja to record them
as dependencies.

## Added `implicit_include_directories` argument to `windows.compile_resources`

[Windows](Windows-module.md) module [compile_resources](Windows-module.md#compile_resources)
now has an `implicit_include_directories` keyword argument to automatically
add current build and source directories to the included paths when compiling
a resource.

## External programs as inputs and dependencies to custom targets

Custom targets now allow specifying an external program in
the `input` and `depends` keyword arguments.  This also applies
to several methods provided by modules, as they are lowered to
custom targets internally. (*Added in 1.11.2*).

## External programs as dependencies to tests

Tests now allow specifying an external program in
the `depends` keyword argument. (*Added in 1.11.2*).
