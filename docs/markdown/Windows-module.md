# Windows module

This module provides functionality used to build applications for
Windows.

## Methods

### compile_resources

*Deprecated since 1.11.0*: Use the [`rc` language](RC.md) instead.
The function continues to work as a thin compatibility shim, but new
projects should use the `rc` language directly.

```
  windows = import('windows')
  windows.compile_resources(...(string | File | CustomTarget | CustomTargetIndex),
                            args: []string,
                            depend_files: [](string | File),
                            depends: [](BuildTarget | CustomTarget | CustomTargetIndex)
                            include_directories: [](IncludeDirectories | string)): [](File | CustomTarget | CustomTargetIndex)
                            implicit_include_directories: bool
```

Compiles Windows `rc` files specified in the positional arguments.
Returns the sources for inclusion in a build target.

*Since 0.61.0* CustomTargetIndexes and CustomTargets with more than one output
may be used as positional arguments.

This method has the following keyword arguments:

- `args` lists extra arguments to pass to the resource compiler
- `depend_files` lists resource files that the resource script depends on
  (e.g. bitmap, cursor, font, html, icon, message table, binary data or manifest
  files referenced by the resource script) (*since 0.47.0*)
- `depends` lists target(s) that this target depends on, even though it does not
  take them as an argument (e.g. as above, but generated) (*since 0.47.0*)
- `include_directories` lists directories to be both searched by the resource
  compiler for referenced resource files, and added to the preprocessor include
  search path.
- `implicit_include_directories` Controls whether Meson adds
  the current source and build directories to the include path (*since 1.11.0*)

#### Migrating to the `rc` language

Replace:

```meson
windows = import('windows')
resources = windows.compile_resources('resource.rc',
  args: ['-DSOME_DEF'],
  depend_files: ['icon.ico', 'manifest.xml'],
  depends: [my_icon_generator],
  include_directories: include_directories('inc'))
executable('myapp', 'main.c', resources)
```

with:

```meson
project('myapp', 'c', 'rc')
add_project_arguments('-DSOME_DEF', language: 'rc')
executable('myapp', 'main.c', 'resource.rc',
           depend_files: ['icon.ico', 'manifest.xml'],
           depends: [my_icon_generator],
           include_directories: include_directories('inc'))
```

The `depend_files` and `depends` keyword arguments can be passed to
the build target instead. However, note that on a build target these
only affect link-step ordering, not individual compile steps. In
practice this is rarely a problem because most `rc` compilers (GNU
`windres`, LLVM `llvm-windres`, and Microsoft `rc.exe` via Meson's
internal wrapper) generate depfiles that let ninja discover included
files automatically at compile time. For `depends`, if the dependency
is a generated `.rc` source, pass it directly as a source to the build
target and the ordering will be handled naturally.
