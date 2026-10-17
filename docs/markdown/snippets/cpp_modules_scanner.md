## Improved C++ modules dependency scanning

The dependency scanner used by the Ninja backend for C++ modules now
understands more of the module syntax:

- dotted module names, such as `export module foo.bar;`
- module partitions, such as `export module foo:part;`, `module foo:part;`
  and `import :part;`
- re-exported imports, such as `export import foo;`
- implementation units (`module foo;`), which depend on the interface of
  their module
- declarations that are indented or that have whitespace around `:`

Comments, string literals and `#if 0` blocks are ignored. Other preprocessor
conditions are not evaluated, therefore some module directive could still
potentially be wrongly interpreted. This is a limitation of the current
implementation.

Module interface units (`.ixx` and `.cppm` files) are no longer put in unity
files, so targets that contain them can now be built with `unity=on`. The
imports of the sources included in a unity file are now taken into account,
and it is an error for a source included in a unity file to be a module unit.

With MSVC, modules are now also scanned for `cpp_std=c++20` and
`cpp_std=vc++20`, and they require Visual Studio 2019 16.10 or newer. With
GCC, the scanner now uses the module files from `gcm.cache`, so targets
using modules are no longer rebuilt every time.
