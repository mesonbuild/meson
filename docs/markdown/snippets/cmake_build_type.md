## Meson now propagates its build type to CMake

When the CMake build type variable, `CMAKE_BUILD_TYPE`, is not set via the
`add_cmake_defines` method of the [`cmake options` object](CMake-module.md#cmake-options-object),
it is inferred from the [Meson build type](Builtin-options.md#details-for-buildtype).
Build types of the two build systems do not match perfectly. The mapping from
Meson build type to CMake build type is as follows:

- `debug` -> `Debug`
- `debugoptimized` -> `RelWithDebInfo`
- `release` -> `Release`
- `minsize` -> `MinSizeRel`

No CMake build type is set for the `plain` Meson build type. The inferred CMake
build type overrides any `CMAKE_BUILD_TYPE` environment variable.
