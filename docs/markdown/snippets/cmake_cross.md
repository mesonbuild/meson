## CMake subproject cross compilation support

Meson now supports cross compilation for CMake subprojects. Meson will try to
automatically guess most of the required CMake toolchain variables from existing
entries in the cross and native files. These variables will be stored in an
automatically generate CMake toolchain file in the build directory. The
remaining variables that can't be guessed can be added by the user in the
new `[cmake]` cross/native file section.
