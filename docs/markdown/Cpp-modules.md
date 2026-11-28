---
title: C++ modules
short-description: Building C++20 modules with the Ninja backend
...

# C++ modules

**Note**: this feature is experimental and not guaranteed to be backwards
compatible or even exist at all in future Meson releases.

Meson can build projects that use C++20 modules, with the Ninja backend only,
and with Ninja 1.10 or newer. A module has to be compiled before the sources
that import it, but which source provides which module is only known by
reading the sources. Meson therefore asks the compiler for the dependencies of
each source before it compiles anything, and gives the result to Ninja as a
[dynamic dependency](https://ninja-build.org/manual.html#ref_dyndep) file.

## When Meson scans for modules

Meson scans the C++ sources of a target if the target, or any target it links
with, shows that it uses modules:

- the arguments that enable modules are in `cpp_args`
  (see the section of each compiler below)
- it has a source with the `.ixx` or `.cppm` extension
- the `cpp_importstd` option is enabled for it

Targets that do not use modules are not scanned, so they do not pay for it.
The value of `cpp_std` does not matter to this decision, but the standard has
to be at least C++20.

The compiler has to be able to describe the modules a source provides and
requires in the P1689 format. A target that uses modules with a compiler that
cannot do that fails at configure time.

## Example

A library that provides a module and a partition, and an executable that
imports it:

```meson
project('modules', 'cpp', default_options: ['cpp_std=c++20'])

cxx = meson.get_compiler('cpp')
if cxx.get_id() == 'msvc'
    modules_args = ['/interface']
elif cxx.version().version_compare('>=15')
    modules_args = ['-fmodules']
else
    modules_args = ['-fmodules-ts']
endif

lib = static_library(
    'lib',
    'lib.cxx',          # export module lib; export import :detail;
    'lib_detail.cxx',   # export module lib:detail;
    cpp_args: modules_args,
)

executable(
    'app',
    'main.cpp',         # import lib;
    link_with: lib,
    cpp_args: modules_args,
)
```

## Compiled modules

Each target writes the compiled form of the modules it provides in its own
private directory, where its object files are. A partition `a:b` is stored as
`a-b`. Therefore, several targets can provide a module with the same name, and
the sources of a target import the module of the targets it links with.

It is an error if the sources of a target import a module which is provided by
several of the targets it can reach, for example because it links with two
libraries which provide the same module. The error names the targets that
provide the module.

## Compilers

### MSVC

- Minimum version: Visual Studio 2022 17.2 (`cl` 19.32), which is the first
  version with `/scanDependencies`.
- Enable modules with `/interface` in `cpp_args`. Sources named `.ixx` or
  `.cppm` are module interface units without any argument, and a target that
  only imports modules does not need one if it links with a target that does.
- The compiled form of a module is written to `<module>.ifc` in the private
  directory of its target.
- `import std` needs Visual Studio 2022 17.14 (`cl` 19.44.35219), and the
  environment variable `VCToolsInstallDir` set by the Visual Studio developer
  environment.

### GCC

- Support for modules is still experimental in GCC itself, expect compiler
  bugs.
- Minimum version: 14, which is the first version with `-fdeps-format`.
- Enable modules with `-fmodules-ts` in `cpp_args` with GCC 14, and with
  `-fmodules` with GCC 15.
- The compiled form of a module is written to `<module>.gcm` in the private
  directory of its target. Meson tells GCC where the modules are with
  `-fmodule-mapper`, and writes the file after scanning the sources, with the
  modules of the target and the ones of the targets it links with.
- Meson adds `-Mno-modules` to the compilation of the targets that use modules,
  because the dependency file GCC writes for modules can not be read by Ninja.
- `import std` needs GCC 15.1.

### clang

- Minimum version: 19, with `clang-scan-deps` of the same version. Meson looks
  for `clang-scan-deps` in the `clang-scan-deps` entry of the `[binaries]`
  section of a [machine file](Machine-files.md), then next to the clang
  compiler (with the same version suffix), then in `PATH`.
- Only finding the dependencies is supported. Meson does not yet pass clang the
  arguments it needs to write and to find the compiled modules, so building
  with modules fails with clang.
- `import std` is not supported.

## `import std`

The `cpp_importstd` option makes Meson build the standard library module
`std` once, and make the targets that enable the option import it. It is
`false` by default, and can be set globally or for a target with
`override_options`.

It is only available with compilers that can build `std`, see their sections
above: MSVC 17.14 and GCC 15.1. The module is built once, and the same
compiled module is used for all targets. Therefore, targets which use
different compiler options (for example a different C++ standard) can not be
mixed. As this is a new feature of compilers, toolchain issues are to be
expected.

## What is supported

- Modules provided and imported across targets, including module partitions
- Several targets providing a module with the same name
- Targets that only import modules, when they link with a target that uses them
- `import std`, with MSVC and GCC
- Scanning with MSVC, GCC and clang

## What is not supported yet

- Building modules with clang
- `import std` with clang
- Backends other than Ninja, and Ninja older than 1.10

## Other compilers and architectures

Other compilers are not supported. Some of them have no modules at all, and
for the others Meson cannot scan the dependencies, among them clang-cl,
Apple Clang, Emscripten, the Intel compilers and the Arm compilers. A target
that uses modules with one of them fails at configure time.

Only x86-64 has been tested. Whether other architectures, and
cross-compilation, work with the compilers above is not known.
