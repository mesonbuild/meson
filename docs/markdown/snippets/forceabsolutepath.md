## New `forceabsolutepath` core option

A new boolean core option `forceabsolutepath` (default `false`) has been added.
When enabled (`meson setup --forceabsolutepath builddir` or
`-Dforceabsolutepath=true`), Meson emits absolute paths to source files and
include directories (`-I`) in the generated build files instead of paths
relative to the build directory.

This is useful when generating coverage reports, where tools such as gcov/lcov
record source paths as seen by the compiler: relative paths like `../src/foo.c`
then end up in the report instead of clean absolute paths rooted at the project.
