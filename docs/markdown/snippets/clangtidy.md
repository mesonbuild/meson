## Clang-tidy target

If `clang-tidy` is installed and the project's source root contains a
`.clang-tidy` (or `_clang-tidy`) file, Meson will automatically define
a `clang-tidy` target that runs Clang-Tidy on all source files.

If you have defined your own `clang-tidy` target, Meson will not
generate its own target.
