---
title: Release 1.9.0
short-description: Release notes for 1.9.0
...

# New features

Meson 1.9.0 was released on 24 August 2025
## Array `.flatten()` method

Arrays now have a `.flatten()` method, which turns nested arrays into a single
flat array. This provides the same effect that Meson often does to arrays
internally, such as when passed to most function arguments.

## `clang-tidy`'s auto-generated targets correctly select source files

In previous versions, the target would run `clang-tidy` on _every_ C-like source files (.c, .h, .cpp, .hpp). It did not work correctly because some files, especially headers, are not intended to be consumed as is.

It will now run only on source files participating in targets.

## Added Qualcomm's embedded linker, eld

Qualcomm recently open-sourced their embedded linker.
https://github.com/qualcomm/eld

Meson users can now use this linker.

## Added suffix function to the FS module

The basename and stem were already available. For completeness, expose also the
suffix.

## Support response files for custom targets

When using the Ninja backend, Meson can now pass arguments to supported tools
through response files.

In this release it's enabled only for the Gnome module, fixing calling
`gnome.mkenums()` with a large set of files on Windows (requires
Glib 2.59 or higher).

## meson format now has a --source-file-path argument when reading from stdin

This argument is mandatory to mix stdin reading with the use of editor config.
It allows to know where to look for the .editorconfig, and to use the right
section of .editorconfig based on the parsed file name.

## Added license keyword to pkgconfig.generate

When specified, it will add a `License:` attribute to the generated .pc file.

## pkgconfig.generate supports internal dependencies in `requires`

Internal dependencies can now be specified to `requires` if
pkgconfig.generate was called on the underlying library.

## New experimental option `rust_dynamic_std`

A new option `rust_dynamic_std` can be used to link Rust programs so
that they use a dynamic library for the Rust `libstd`.

Right now, `staticlib` crates cannot be produced if `rust_dynamic_std` is
true, but this may change in the future.

## Rust and non-Rust sources in the same target

Meson now supports creating a single target with Rust and non Rust
sources mixed together.  In this case, if specified, `link_language`
must be set to `rust`.

## Explicitly setting Swift module name is now supported

It is now possible to set the Swift module name for a target via the
*swift_module_name* target kwarg, overriding the default inferred from the
target name.

```meson
lib = library('foo', 'foo.swift', swift_module_name: 'Foo')
```

## Top-level statement handling in Swift libraries

The Swift compiler normally treats modules with a single source
file (and files named main.swift) to run top-level code at program
start. This emits a main symbol which is usually undesirable in a
library target. Meson now automatically passes the *-parse-as-library*
flag to the Swift compiler in case of single-file library targets to
disable this behavior unless the source file is called main.swift.

## Swift compiler receives select C family compiler options

Meson now passes select few C family (C/C++/Obj-C/Obj-C++) compiler
options to the Swift compiler, notably *-std=*, in order to improve
the compatibility of C code as interpreted by the C compiler and the
Swift compiler.

NB: This does not include any of the options set in the target's
c_flags.

## Swift/C++ interoperability is now supported

It is now possible to create Swift executables that can link to C++ or
Objective-C++ libraries. To enable this feature, set the target kwarg
_swift\_interoperability\_mode_ to 'cpp'.

To import C++ code, specify a bridging header in the Swift target's
sources, or use another way such as adding a directory containing a
Clang module map to its include path.

Note: Enabling C++ interoperability in a library target is a breaking
change. Swift libraries that enable it need their consumers to enable
it as well, as per [the Swift documentation][1].

Swift 5.9 is required to use this feature. Xcode 15 is required if the
Xcode backend is used.

```meson
lib = static_library('mylib', 'mylib.cpp')
exe = executable('prog', 'main.swift', 'mylib.h', link_with: lib, swift_interoperability_mode: 'cpp')
```

[1]: https://www.swift.org/documentation/cxx-interop/project-build-setup/#vending-packages-that-enable-c-interoperability

## Support for MASM in Visual Studio backends

Previously, assembling `.masm` files with Microsoft's Macro Assembler is only
available on the Ninja backend. This now also works on Visual Studio backends.

Note that building ARM64EC code using `ml64.exe` is currently unimplemented in
both of the backends. If you need mixing x64 and Arm64 in your project, please
file an issue on GitHub.

## Limited support for WrapDB v1

WrapDB v1 has been discontinued for several years, Meson will now print a
deprecation warning if a v1 URL is still being used. Wraps can be updated to
latest version using `meson wrap update` command.

