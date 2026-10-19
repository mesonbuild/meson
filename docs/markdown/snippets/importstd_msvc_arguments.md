## `import std` with MSVC uses the arguments of the targets

With the `cpp_importstd` option and the MSVC compiler, meson now builds the
module with the arguments of the targets that matter to the compiler when it
imports the module: the C runtime, the character set, the C++ standard, the
exception and floating point options, the macros read by the standard library,
and so on. This prevents reporting a C505 warning, which would become an error
if using `werror`. Arguments that do not matter, such as warnings, optimization
and include directories, are ignored. A module is built for each different set
of arguments, and shared by the targets that have the same one, so the files in
the build directory are named `std.<id>.ifc`.

The module is no longer built through a compiler cache, which cannot restore it.
