---
title: Release 1.5.0
short-description: Release notes for 1.5.0
...

# New features

Meson 1.5.0 was released on 10 July 2024
## Support for `bztar` in `meson dist`

The `bztar` format is now supported in `meson dist`. This format is also known
as `bzip2`.

## Cargo dependencies names now include the API version

Cargo dependencies names are now in the format `<package_name>-<version>-rs`:
- `package_name` is defined in `[package] name = ...` section of the `Cargo.toml`.
- `version` is the API version deduced from `[package] version = ...` as follow:
  * `x.y.z` -> 'x'
  * `0.x.y` -> '0.x'
  * `0.0.x` -> '0'
  It allows to make different dependencies for uncompatible versions of the same
  crate.
- `-rs` suffix is added to distinguish from regular system dependencies, for
  example `gstreamer-1.0` is a system pkg-config dependency and `gstreamer-0.22-rs`
  is a Cargo dependency.

That means the `.wrap` file should have `dependency_names = foo-1-rs` in their
`[provide]` section when `Cargo.toml` has package name `foo` and version `1.2`.

This is a breaking change (Cargo subprojects are still experimental), previous
versions were using `<package_name>-rs` format.

## Added support `Cargo.lock` file

When a (sub)project has a `Cargo.lock` file at its root, it is loaded to provide
an automatic fallback for dependencies it defines, fetching code from
https://crates.io or git. This is identical as providing `subprojects/*.wrap`,
see [cargo wraps](Wrap-dependency-system-manual.md#cargo-wraps) dependency naming convention.

## Meson now propagates its build type to CMake

When the CMake build type variable, `CMAKE_BUILD_TYPE`, is not set via the
`add_cmake_defines` method of the [`cmake options` object](CMake-module.md#cmake-options-object),
it is inferred from the [Meson build type](Builtin-options.md#details-for-buildtype).
Build types of the two build systems do not match perfectly. The mapping from
Meson build type to CMake build type is as follows:

- `debug` -> `Debug`
- `debugoptimized` -> `RelWithDebInfo`
- `release` -> `Release`
- `minsize` -> `MinSizeRel`

No CMake build type is set for the `plain` Meson build type. The inferred CMake
build type overrides any `CMAKE_BUILD_TYPE` environment variable.

## compiler.run() method is now available for all languages

It used to be only implemented for C-like and D languages, but it is now available
for all languages.

## dependencies created by compiler.find_library implement the `name()` method

Previously, for a [[@dep]] that might be returned by either [[dependency]] or
[[compiler.find_library]], the method might or might not exist with no way
of telling.

## New version_argument kwarg for find_program

When finding an external program with `find_program`, the `version_argument`
can be used to override the default `--version` argument when trying to parse
the version of the program.

For example, if the following is used:
```meson
foo = find_program('foo', version_argument: '-version')
```

meson will internally run `foo -version` when trying to find the version of `foo`.

## Meson configure handles changes to options in more cases

Meson configure now correctly handles updates to the options file without a full
reconfigure. This allows making a change to the `meson.options` or
`meson_options.txt` file without a reconfigure.

For example, this now works:
```sh
meson setup builddir
git pull
meson configure builddir -Doption-added-by-pull=value
```

## New meson format command

This command is similar to `muon fmt` and allows to format a `meson.build`
document.

## Added support for GCC's `null_terminated_string_arg` function attribute

You can now check if a compiler support the `null_terminated_string_arg`
function attribute via the `has_function_attribute()` method on the
[[@compiler]] object.

```meson
cc = meson.get_compiler('c')

if cc.has_function_attribute('null_terminated_string_arg')
  # We have it...
endif
```

## A new dependency for ObjFW is now supported

For example, you can create a simple application written using ObjFW like this:

```meson
project('SimpleApp', 'objc')

objfw_dep = dependency('objfw', version: '>= 1.0')

executable('SimpleApp', 'SimpleApp.m',
  dependencies: [objfw_dep])
```

Modules are also supported. A test case using ObjFWTest can be created like
this:

```meson
project('Tests', 'objc')

objfwtest_dep = dependency('objfw', version: '>= 1.1', modules: ['ObjFWTest'])

executable('Tests', ['FooTest.m', 'BarTest.m'],
  dependencies: [objfwtest_dep])
```

## Support of indexed `@PLAINNAME@` and `@BASENAME@`

In `custom_target()` and `configure_file()` with multiple inputs,
it is now possible to specify index for `@PLAINNAME@` and `@BASENAME@`
macros in `output`:
```
custom_target('target_name',
  output: '@PLAINNAME0@.dl',
  input: [dep1, dep2],
  command: cmd)
```

## Required kwarg on more `compiler` methods

The following `compiler` methods now support the `required` keyword argument:

- `compiler.compiles()`
- `compiler.links()`
- `compiler.runs()`

```meson
cc.compiles(valid, name: 'valid', required : true)
cc.links(valid, name: 'valid', required : true)
cc.run(valid, name: 'valid', required : true)

assert(not cc.compiles(valid, name: 'valid', required : opt))
assert(not cc.links(valid, name: 'valid', required : opt))
res = cc.run(valid, name: 'valid', required : opt)
assert(res.compiled())
assert(res.returncode() == 0)
assert(res.stdout() == '')
assert(res.stderr() == '')
```

## The Meson test program supports a new "--interactive" argument

`meson test --interactive` invokes tests with stdout, stdin and stderr
connected directly to the calling terminal. This can be useful when running
integration tests that run in containers or virtual machines which can spawn a
debug shell if a test fails.

## meson test now sets the `MESON_TEST_ITERATION` environment variable

`meson test` will now set the `MESON_TEST_ITERATION` environment variable to the
current iteration of the test. This will always be `1` unless `--repeat` is used
to run the same test multiple times.

## The Meson test program supports a new "--max-lines" argument

By default `meson test` only shows the last 100 lines of test output from tests
that produce large amounts of output. This default can now be changed with the
new `--max-lines` option. For example, `--max-lines=1000` will increase the
maximum number of log output lines from 100 to 1000.

## Basic support for TI Arm Clang (tiarmclang)

Support for TI's newer [Clang-based ARM toolchain](https://www.ti.com/tool/ARM-CGT).

## Support for Texas Instruments C6000 C/C++ compiler

Meson now supports the TI C6000 C/C++ compiler use for the C6000 cpu family.
The example cross file is available in `cross/ti-c6000.txt`.

## Wayland stable protocols can be versioned

The wayland module now accepts a version number for stable protocols.

```meson
wl_mod = import('unstable-wayland')

wl_mod.find_protocol(
  'linux-dmabuf',
  state: 'stable'
  version: 1
)
```

