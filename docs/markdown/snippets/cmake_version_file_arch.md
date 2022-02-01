## arch_independent kwarg in cmake.write_basic_package_version_file

The `write_basic_package_version_file()` function from the `cmake` module
now supports an `arch_independent` kwarg, so that architecture checks in
the generated Package Version file are skipped, reproducing the behaviour of
CMake's [ARCH_INDEPENDENT](https://cmake.org/cmake/help/latest/module/CMakePackageConfigHelpers.html#command:write_basic_package_version_file)
option.
