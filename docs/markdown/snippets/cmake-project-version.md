## Meson now reads the project version of cmake subprojects

CMake subprojects configured by meson will now have their project
version set to the project version in their CMakeLists.txt. This
allows version constraints to be properly checked when falling back to
a cmake subproject.
