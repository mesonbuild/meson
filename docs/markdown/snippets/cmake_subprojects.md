## CMake subprojects

Meson can now directly consume CMake based subprojects. Using CMake
subprojects is almost identical to using the "normal" meson subprojects:

```meson
sub_proj = subproject('libsimple_cmake', method : 'cmake')
```

The `method` key is optional if the subproject only has a `CMakeList.txt`.
Without specifying a method meson will always first try to find and use a
`meson.build` in the subproject.

Project specific CMake options can be added with the new `cmake_options` key.

The returned `sub_proj` supports the same options as a "normal" subproject.
Meson automatically detects build targets, which can be retrieved with
`get_variable`. Meson also generates a dependency object for each target.

These variable names are generated based on the CMake target name.

```cmake
add_library(cm_exe SHARED ${SOURCES})
```

For `cm_exe`, meson will then define the following variables:

- `cm_exe` The raw library target (similar to `cm_exe = library('cm_exe', ...)` in meson)
- `cm_exe_dep` The dependency object for the target (similar to `declare_dependency()` in meson)
- `cm_exe_inc` A meson include directory object, containing all include irectories of the target.

It should be noted that not all projects are guaranteed to work. The
safest approach would still be to create a `meson.build` for the
subprojects in question.
