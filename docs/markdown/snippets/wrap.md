## Automatic fallback to `cmake` and `cargo` subproject

CMake subprojects have been supported for a while using the `cmake.subproject()`
module method. However until now it was not possible to use a CMake subproject
as fallback in a `dependency()` call.

A wrap file can now specify the method used to build it by setting the `method`
key in the wrap file's first section. The method defaults to `meson`.

Supported methods:
- `meson` requires `meson.build` file.
- `cmake` requires `CMakeLists.txt` file. [See details](Wrap-dependency-system-manual.md#cmake-wraps).
- `cargo` requires `Cargo.toml` file. [See details](Wrap-dependency-system-manual.md#cargo-wraps).
