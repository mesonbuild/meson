## Swift/C++ interoperability is now supported

It is now possible to create Swift executables that can link to C++ or
Objective-C++ libraries. To enable this feature, set the target kwarg
_swift\_interoperability\_mode_ to 'cpp'.

To import C++ code, specify a bridging header in the Swift target's
sources, or use another way such as adding a directory containing a
Clang module map to its include path.

Note: Enabling C++ interoperability in a library target is a breaking
change. Swift libraries that enable it need their consumers to enable
it as well, as per [the Swift documentation][1].

Swift 5.9 is required to use this feature. Xcode 15 is required if the
Xcode backend is used.

```meson
lib = static_library('mylib', 'mylib.cpp')
exe = executable('prog', 'main.swift', 'mylib.h', link_with: lib, swift_interoperability_mode: 'cpp')
```

[1]: https://www.swift.org/documentation/cxx-interop/project-build-setup/#vending-packages-that-enable-c-interoperability
