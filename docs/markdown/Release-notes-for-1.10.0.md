---
title: Release 1.10.0
short-description: Release notes for 1.10.0
...

# New features

Meson 1.10.0 was released on 08 December 2025
## Support for the `counted_by` attribute

`compiler.has_function_attribute()` now supports for the new `counted_by`
attribute.

## Added a `values()` method for dictionaries

Mesons built-in [[@dict]] type now supports the [[dict.values]] method
to retrieve the dictionary values as an array, analogous to the
[[dict.keys]] method.

```meson
dict = { 'b': 'world', 'a': 'hello' }

[[#dict.keys]] # Returns ['a', 'b']
[[#dict.values]] # Returns ['hello', 'world']
```

## Add cmd_array method to ExternalProgram

Added a new `cmd_array()` method to the `ExternalProgram` object that returns
an array containing the command(s) for the program. This is particularly useful
in cases like pyInstaller where the Python command is `meson.exe runpython`,
and the full path should not be used but rather the command array.

The method returns a list of strings representing the complete command needed
to execute the external program, which may differ from just the full path
returned by `full_path()` in cases where wrapper commands or interpreters are
involved.

## Microchip XC32 compiler support

The Microchip XC32 compiler is now supported.

## Added OS/2 support

Meson now supports OS/2 system. Especially, `shortname` kwarg and
`os2_emxomf` builtin option are introduced.

`shortname` is used to specify a short DLL name fitting to a 8.3 rule.

```meson
lib = library('foo_library',
    ...
    shortname: 'foo',
    ...
)
```

This will generate `foo.dll` not `foo_library.dll` on OS/2. If
`shortname` is not used, `foo_libr.dll` which is truncated up to 8
characters is generated.

`os2_emxomf` is used to generate OMF files with OMF tool-chains.

```
meson setup --os2-emxomf builddir
```

This will generate OMF object files and `.lib` library files. If
`--os2-emxomf` is not used, AOUT object files and `.a` library files are
generated.

## Android cross file generator

The `env2mfile` command now supports a `--android` argument. When
specified, it tells the cross file generator to create cross files for
all Android toolchains located on the current machines.

This typically creates many files, so the `-o` argument specifies the
output directory. A typical use case goes like this:

```
meson env2mfile --android -o androidcross
meson setup --cross-file \
  androidcross/android-29.0.14033849-android35-aarch64-cross.txt \
  builddir
```

## Array `.slice()` method

Arrays now have a `.slice()` method which allows for subsetting of arrays.

## `-Db_vscrt` on clang

`-Db_vscrt` will now link the appropriate runtime library, and set
the appropriate preprocessor symbols, also when the compiler is clang.
This is only supported when using `link.exe` or `lld-link.exe` as the
linker.

## Added `build_subdir` arg to various targets

`custom_target()`, `build_target()` and `configure_file()` now support
the `build_subdir` argument. This directs Meson to place the build
result within the specified sub-directory path of the build directory.

```meson
configure_file(input : files('config.h.in'),
               output : 'config.h',
               build_subdir : 'config-subdir',
               install_dir : 'share/appdir',
               configuration : conf)
```

This places the build result, `config.h`, in a sub-directory named
`config-subdir`, creating it if necessary. To prevent collisions
within the build directory, `build_subdir` is not allowed to match a
file or directory in the source directory nor contain '..' to refer to
the parent of the build directory. `build_subdir` does not affect the
install directory path at all; `config.h` will be installed as
`share/appdir/config.h`. `build_subdir` may contain multiple levels of
directory names.

This allows construction of files within the build system that have
any required trailing path name components as well as building
multiple files with the same basename from the same source directory.

## Support for Cargo workspaces

When parsing `Cargo.toml` files, Meson now recognizes workspaces
and will process all the required members and any requested optional
members of the workspace.

For the time being it is recommended to regroup all Cargo dependencies inside a
single workspace invoked from the main Meson project. When invoking multiple
different Cargo subprojects from Meson, feature resolution of common
dependencies might be wrong.

## Experimental Codegen module

A new module wrapping some common code generators has been added. Currently it supports lex/flex and yacc/bison.

## Methods from compiler object now accept strings for include_directories

The various [[@compiler]] methods with a `include_directories` keyword argument
now accept strings or array of strings, in addition to [[@inc]] objects
generated from [[include_directories]] function, as it was already the case for
[[build_target]] family of functions.

## `meson format` has a new `--check-diff` option

When using `meson format --check-only` to verify formatting in CI, it would
previously silently exit with an error code if the code was not formatted
correctly.

A new `--check-diff` option has been added which will instead print a diff of
the required changes and then exit with an error code.

## `-Db_thinlto_cache` now supported for GCC

`-Db_thinlto_cache` is now supported for GCC 15's incremental LTO, as is
`-Db_thinlto_cache_dir`.

## Using `meson.get_compiler()` to get a language from another project is marked broken

Meson currently will return a compiler instance from the `meson.get_compiler()`
call, if that language has been initialized in any project. This can result in
situations where a project can only work as a subproject, or if a dependency is
provided by a subproject rather than by a pre-built dependency.

## Experimental C++ import std support

**Note**: this feature is experimental and not guaranteed to be
  backwards compatible or even exist at all in future Meson releases.

Meson now supports `import std`, a new, modular way of using the C++
standard library. This support is enabled with the new `cpp_importstd`
option. It defaults to `false`, but you can set it to `true` either
globally or per-target using `override_options` in the usual way.

The implementation has many limitations. The biggest one is that the
same module file is used on _all_ targets. That means you can not mix
multiple different C++ standards versions as the compiled module file
can only be used with the same compiler options as were used to build
it. This feature only works with the Ninja backend.

As `import std` is a major new feature in compilers, expect to
encounter toolchain issues when using it. For an example [see
here](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=122614).

## Common `Cargo.lock` for all Cargo subprojects

Whenever Meson finds a `Cargo.lock` file in the toplevel directory
of the project, it will use it to resolve the versions of Cargo
subprojects in preference to per-subproject `Cargo.lock` files.
Per-subproject lock files are only used if the invoking project
did not have a `Cargo.lock` file itself.

If you wish to experiment with Cargo subprojects, it is recommended
to use `cargo` to set up `Cargo.lock` and `Cargo.toml` files,
encompassing all Rust targets, in the toplevel source directory.
Cargo subprojects remain unstable and subject to change.

## Add a configure log in meson-logs

Add a second log file `meson-setup.txt` which contains the configure logs
displayed on stdout during the meson `setup` stage.
It allows user to navigate through the setup logs without searching in the terminal
or the extensive information of `meson-log.txt`.

## Added new `namingscheme` option

Traditionally Meson has named output targets so that they don't clash
with each other. This has meant, among other things, that on Windows
Meson uses a nonstandard `.a` suffix for static libraries because both
static libraries and import libraries have the suffix `.lib`.

There is now an option `namingscheme` that can be set to
`platform`. This new platform native naming scheme that replicates
what Rust does. That is, shared libraries on Windows get a suffix
`.dll`, static libraries get `.lib` and import libraries have the name
`.dll.lib`.

We expect to change the default value of this option to `platform` in
a future major version. Until that happens we reserve the right to
alter how `platform` actually names its output files.

## Rewriter improvements

The [rewriter](Rewriter.md) added support for writing the `project()`
`license_files` argument and for reading dict-valued kwargs.

It also removed the unused but mandatory `value` arguments to the
`default-options delete` and `kwargs delete` CLI subcommands.  To allow
scripts to continue supporting previous releases, these arguments are
still accepted (with a warning) if they're all equal to the empty string.

## Passing `-C default-linker-libraries` to rustc

When calling rustc, Meson now passes the `-C default-linker-libraries` option.
While rustc passes the necessary libraries for Rust programs, they are rarely
enough for mixed Rust/C programs.

## `rustc` will receive `-C embed-bitcode=no` and `-C lto` command line options

With this release, Meson passes command line arguments to `rustc` to
enable LTO when the `b_lto` built-in option is set to true.  As an
optimization, Meson also passes `-C embed-bitcode=no` when LTO is
disabled; note that this is incompatible with passing `-C lto` via
`rust_args`.

## New method to handle GNU and Windows symbol visibility for C/C++/ObjC/ObjC++

Defining public API of a cross platform C/C++/ObjC/ObjC++ library is often
painful and requires copying macro snippets into every projects, typically using
`__declspec(dllexport)`, `__declspec(dllimport)` or
`__attribute__((visibility("default")))`.

Meson can now generate a header file that defines exactly what's needed for
all supported platforms:
[`snippets.symbol_visibility_header()`](Snippets-module.md#symbol_visibility_header).

## Vala BuildTarget dependency enhancements

A BuildTarget that has Vala sources can now get a File dependency for its
generated header, vapi, and gir files.

```meson
lib = library('foo', 'foo.vala')
lib_h = lib.vala_header()
lib_s = static_lib('static', 'static.c', lib_h)

lib_vapi = lib.vala_vapi()

custom_target(
  'foo-typelib',
  command : ['g-ir-compiler', '--output', '@OUTPUT@', '@INPUT@'],
  input : lib.vala_gir(),
  output : 'Foo-1.0.typelib'
)
```

`static.c` will not start compilation until `lib.h` is generated.

## `i18n.xgettext` now accepts CustomTarget and CustomTargetIndex as sources

Previously, [[@custom_tgt]] were accepted but silently ignored, and
[[@custom_idx]] were not accepted.

Now, they both can be used, and the generated outputs will be scanned to extract
translation strings.
