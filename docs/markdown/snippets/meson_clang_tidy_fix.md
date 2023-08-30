## clang-tidy-fix target

If `clang-tidy` is installed and the project's source root contains a
`.clang-tidy` (or `_clang-tidy`) file, Meson will automatically define
a `clang-tidy-fix` target that runs `run-clang-tidy` tool with `-fix`
option to apply the changes found by clang-tidy to the source code.

If you have defined your own `clang-tidy-fix` target, Meson will not
generate its own target.
