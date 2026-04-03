---
title: RC
short-description: Compiling Windows resources
...

# Compiling Windows resources

*Since 1.11.0*

Meson has support for compiling Windows resource files (`.rc`). To use
it, add `rc` to your project languages:

```meson
project('myapp', 'c', 'rc')

executable('myapp', 'main.c', 'resources.rc')
```

You can also add the language conditionally, which is useful for
cross-compilation setups where an RC compiler may not always be
available:

```meson
project('myapp', 'c')

if add_languages('rc', required: false, native: false)
  # .rc sources can be used in targets
endif
```

## Compiler detection

The following resource compilers are detected automatically:

| Compiler id   | Tool        | CLI style  |
|---------------|-------------|------------|
| rc            | Microsoft `rc.exe` | MSVC |
| llvm-rc       | LLVM `llvm-rc`     | MSVC |
| windres       | GNU `windres`      | GCC  |
| llvm-windres  | LLVM `llvm-windres`| GCC  |
| wrc           | Wine `wrc`         | GCC  |

Meson will look for the `rc` binary in the `[binaries]` section of
your machine file, or through the `RC` and `WINDRES` environment
variables.

## Passing arguments

Extra flags can be passed to the resource compiler using the standard
Meson mechanisms:

```meson
# Via project arguments
add_project_arguments('-DPROJECT_DEF', language: 'rc')

# Via per-target keyword argument
executable('myapp', 'main.c', 'resources.rc',
           rc_args: ['-DLIB_BUILD'])
```

The `RCFLAGS` environment variable is also respected.

## Include directories

Include directories work the same as for other languages:

```meson
inc = include_directories('res')
executable('myapp', 'main.c', 'resources.rc',
           include_directories: inc)
```

