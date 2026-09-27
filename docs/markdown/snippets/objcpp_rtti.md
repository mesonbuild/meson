## `cpp_rtti` is honored for Objective-C++

The `cpp_rtti` option is now respected when compiling Objective-C++
sources. Setting `cpp_rtti=false` passes `-fno-rtti` for `.mm` files,
just like it already did for C++ sources.
