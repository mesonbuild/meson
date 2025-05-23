## Swift/C++ interoperability is now supported

It is now possible to create Swift executables that can link to C++ or
Objective-C++ libraries. Only specifying a bridging header for the Swift
target is required.

Swift 5.9 is required to use this feature. Xcode 15 is required if the
Xcode backend is used.

```meson
lib = static_library('mylib', 'mylib.cpp')
exe = executable('prog', 'main.swift', 'mylib.h', link_with: lib)
```
