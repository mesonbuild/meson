---
title: Swift
short-description: Compiling Swift sources
---

# Compiling Swift applications

Meson has support for compiling Swift programs. A minimal *meson.build* file for Swift looks like this:

```meson
project('myapp', 'swift')

executable('myapp', 'main.swift')
```

The Swift language version can be set using the *swift_std* option.

```meson
project('myapp', 'swift', default_options: {'swift_std': '6'})

executable('myapp', 'main.swift')
```

# Library linking

Meson supports creating both static and shared Swift libraries.
To link a Swift target to another, add it to the *link_with* kwarg of the target it should be linked into.
The library will then be available for use in the other target.

It is currently not possible to add a Swift library's interface to another target without linking the library, or
vice-versa.

# Handling of top-level code

By default, the Swift compiler treats top-level code in a file as the program entry-point when either the file is named
'main.swift', or it is the single Swift source file in the module.

This behavior can be suppressed by passing the *-parse-as-library* compiler option, in which case it will not treat
top-level code as the entry-point. Meson automatically passes the *-parse-as-library* option when the target is a
library, contains only one source file, and the source file is not named 'main.swift', in order to make single-file
library targets not generate a main symbol.

This makes the default behavior as follows.

<table>
<tr><td>Entry-point?</td><th>main.swift</th><th>Other name</th></tr>
<tr><th>Single-file target</th><td>Always</td><td>In executable targets</td></tr>
<tr><th>Multi-file target</th><td>Always</td><td>Never</td></tr>
</table>

If a file is treated as the entry-point where it should not, for example when it contains a type annotated with *@main*,
you can add the *-parse-as-library* option to the target manually.

```meson
project('myapp', 'swift')

executable('myapp', 'MyApp.swift', swift_args: ['-parse-as-library'])
```

# Using C/C++/Objective-C code from Swift

Swift has support for importing and using C/C++/Objective-C (henceforth called "C-family") libraries directly. For this
to work however, they must supply a [Clang module][1] in the form of a *module.modulemap* file declaring the module name
and headers to import.

This module file should usually be supplied by the dependency at the root of its include directory. In case of its
absence, you can add a substitute in your project.
[The official documentation][2] suggests constructing a VFS overlay, however there is a simpler way to do it by adding
an include directory containing the *module.modulemap* file and a header next to it importing the real library headers.

Keeping the SQLite example from the documentation linked above, it can be made available as a Swift module in the
following way.

```modulemap
// Headers/CSQLite/module.modulemap
module CSQLite {
    header "sqlite3.h"
}
```

```c
// Headers/CSQLite/sqlite3.h
#include_next "sqlite3.h"
```

```swift
// main.swift
import CSQLite

var db: OpaquePointer? = nil

let res = sqlite3_open("", &db)
precondition(res == SQLITE_OK)

print("\(db!)")

sqlite3_close(db)
```

```meson
project('myapp', 'swift', 'c')

sqlite_dep = dependency('sqlite3')
csqlite_dep = declare_dependency(include_directories: ['Headers/CSQLite'], dependencies: [sqlite_dep])

executable('myapp', 'main.swift', dependencies: [csqlite_dep])
```

Another way of making C-family code available to a Swift executable is by way of a *bridging header*, conventionally
named 'Bridging-Header.h'. This is a C-family header which is specified as part of the target's source files, and
symbols defined in it or included from it are automatically made available to the Swift code. Note that bridging headers
can only be used in executable targets and not library targets, as they cannot be included as part of the generated
Swift module interface that is used when consuming library targets.

```c
// Bridging-Header.h
struct Foo {
    int x;
};
```

```swift
// main.swift
let foo = Foo(x: 1)
```

```meson
project('myapp', 'swift', 'c')

executable('myapp', 'main.swift', 'Bridging-Header.h')
```

To be able to import C++ libraries, the target must additionally have the *swift_interoperability_mode* kwarg set to
'cpp'. Note that enabling C++ interoperability in a library target is a breaking change. Swift libraries that enable it
need their consumers to enable it as well, as per [the Swift documentation][3].

```meson
lib = static_library('mylib', 'mylib.cpp')
exe = executable('myapp', 'main.swift', 'Bridging-Header.h', link_with: lib, swift_interoperability_mode: 'cpp')
```

Note that Objective-C support is currently only available on Apple platforms with the system Objective-C runtime, and
will not work with different implementations like GNUstep.

[1]: https://clang.llvm.org/docs/Modules.html
[2]: https://www.swift.org/documentation/articles/wrapping-c-cpp-library-in-swift.html
[3]: https://www.swift.org/documentation/cxx-interop/project-build-setup/#vending-packages-that-enable-c-interoperability

# Using Swift code from C-family languages

to do

# Using Swift and C-family code in the same target

to do

# Swift module names

Swift modules (i.e. libraries and executables) have a module name, which is the name under which they can be imported.
By default, this is set to the name of the Meson target. If this is undesirable, for example when building a library for
both the host and build platform, it can be manually specified with the swift_module_name kwarg on the target.

```meson
project('myapp', 'swift')

library('MyLibrary-native', 'MyLibrary.swift', swift_module_name: 'MyLibrary', native: true)
library('MyLibrary', 'MyLibrary.swift')
```

# Caveats

## Installing libraries and finding dependencies

Installing Swift module interface and writing pkg-config files for it is currently not implemented.

## SwiftPM integration

Meson does not currently support importing SwiftPM packages (Package.swift) directly. To use these packages, Meson build
files must be hand-written for the dependency.

## Package-level visibility

Meson does not automatically set up package-level visibility for targets. To use this in Swift code, add the
*-package-name* flag to swift_args with a unique name.

```meson
project('myapp', 'swift')

myapp_package = ['-package-name', 'myapp']

lib = library('applib', 'Library.swift', swift_args: [myapp_package])
executable('myapp', 'main.swift', dependencies: [lib], swift_args: [myapp_package])
```

## Toolchain compatibility

The Swift toolchain ships its own Clang compiler. On systems other than macOS, this is usually not the default C
compiler. If interoperability with C++ is a concern, it is advised to use the Clang compiler in the Swift toolchain to
compile C/C++ code, especially when using Swift code from C++.

On non-macOS systems that use LLVM libc++ as the system's C++ STL implementation, be aware that the libc++ version has
to be compatible with the Clang version shipped in the Swift compiler, which is often several major versions behind.
Libc++ currently supports the same major version of Clang and additionally the previous two major versions, for example
Clang 18, 19, 20 for libc++ 20. You may have to hold back major version updates for libc++ on such a system to stay
compatible with Swift.

## ABI stability

While Meson allows building and installing Swift libraries on any platform, be aware that Swift only has a stable ABI
on Apple platforms.

## Bundles

Meson does not currently support automatically producing bundles for use with the Foundation.Bundle class.
