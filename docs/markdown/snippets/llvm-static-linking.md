# LLVM dependency supports both dynamic and static linking

The LLVM dependency has been improved to consistently use dynamic linking.
Previously recent version (>= 3.9) would link dynamically while older versions
would link statically.

Now LLVM also accepts the `static` keyword to enable statically linking to LLVM
modules instead of dynamically linking.
