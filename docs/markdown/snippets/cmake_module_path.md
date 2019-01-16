## Added `module_path` and `cmake_args` to dependency

The CMake dependency backend can now make use of existing `Find<name>.cmake`
files by setting the `CMAKE_MODULE_PATH` with the new `dependency()` property
`module_path`. The paths given to `module_path` should be relative to the
project source directory.

Furthermore the property `cmake_args` was added to give CMake additional
parameters.
