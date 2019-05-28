## CMake subprojects

Meson can now directly consume CMake based subprojects with the
CMake module.

Using CMake subprojects is similar to using the "normal" meson
subprojects. They also have to be located in the `subprojects`
directory.

Example:

```cmake
add_library(cm_lib SHARED ${SOURCES})
```

```meson
cmake = import('cmake')

# Configure the CMake project
sub_proj = cmake.subproject('libsimple_cmake')

# Fetch the dependency object
cm_lib = sub_proj.dependency('cm_lib')

executable(exe1, ['sources'], dependencies: [cm_lib])
```

It should be noted that not all projects are guaranteed to work. The
safest approach would still be to create a `meson.build` for the
subprojects in question.
