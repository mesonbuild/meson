## C++ modules are scanned by the compiler

With the Ninja backend, the dependencies of C++ modules are now found by the
compiler itself instead of by a scanner built into Meson. Each C++ source of a
target that uses modules is scanned with:

- `/scanDependencies` with MSVC
- `-fdeps-format=p1689r5` with GCC
- `clang-scan-deps` with clang

This requires at least Visual Studio 2022 17.2 (`cl` 19.32), GCC 14 or clang 19.
A target that uses modules with an older compiler now fails to configure with
an error asking for a more recent compiler. The scanner built into Meson 
(depscan.py) is still used for Fortran.

A target is scanned for modules if one of the following is true, for the target
or for any target it links with:

- a compiler argument that enables modules is in its `cpp_args`
  (`/interface` with MSVC, `-fmodules-ts` with GCC 14, `-fmodules` with GCC 15)
- it has a source with the `.ixx` or `.cppm` extension
- the `cpp_importstd` option is enabled

Whether `cpp_std` is `c++latest` is no longer taken into account.

With MSVC and GCC, each target now writes the compiled form of its modules in
its own private directory, so several targets can provide a module with the same
name. It is an error if the sources of a target import a module that is provided
by several targets it links with.

With GCC, the dependency file of a target that uses modules no longer makes Ninja
fail with `input may not also have inputs`.

Scanning with clang finds the dependencies between modules, but Meson does not
yet pass clang the arguments it needs to build and import module files.
