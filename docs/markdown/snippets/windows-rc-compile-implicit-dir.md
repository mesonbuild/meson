## Added `implicit_include_directories` argument to `windows.compile_resources`

[Windows](Windows-module.md) module [compile_resources](Windows-module.md#compile_resources)
now have a `implicit_include_directories` keyword argument to automatically
add current build and source directories to the included paths when compiling
a resource.
