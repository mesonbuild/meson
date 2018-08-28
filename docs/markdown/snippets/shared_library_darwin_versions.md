## `shared_library()` now supports setting dylib compatibility and current version

Now, by default `shared_library()` sets `-compatibility_version` and
`-current_version` of a macOS dylib using the `soversion`.

This can be overriden by using the `darwin_versions:` kwarg to
[`shared_library()`](Reference-manual.md#shared_library). As usual, you can
also pass this kwarg to `library()` or `build_target()` and it will be used in
the appropriate circumstances.
