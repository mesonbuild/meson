---
short-description: Setting up native compilation
...

# Persistent native environments

New in 0.49.0

Meson has [cross files for describing cross compilation environments](Cross-compilation.md),
for describing native environments it has equivalent "native files".

Natives describe the *build machine*, and can be used to override properties of
non-cross builds, as well as properties that are marked as "native" in a cross
build.

There are a couple of reasons you might want to use a native file to keep a
persistent environment:

* To build with a non-default native tool chain (such as clang instead of gcc)
* To use a non-default version of another binary, such as yacc, or llvm-config


## Changing native file settings

All of the rules about cross files and changed settings apply to native files
as well, see [here](Cross-compilation.md#Changing-cross-file-settings)


## Defining the environment

### Binaries

Currently the only use of native files is to override native binaries. This
includes the compilers and binaries collected with `find_program`, and those
used by dependencies that use a config-tool instead of pkgconfig for detection,
like `llvm-config`

```ini
[binaries]
c = '/usr/local/bin/clang'
cpp = '/usr/local/bin/clang++'
rust = '/usr/local/bin/rust'
llvm-config = '/usr/local/llvm-svn/bin/llvm-config'
```

### Paths and Directories

As of 0.50.0 paths and directories such as libdir can be defined in the native
file in a paths section

```ini
[paths]
libdir = 'mylibdir'
prefix = '/my prefix'
```

These values will only be loaded when not cross compiling. Any arguments on the
command line will override any options in the native file. For example, passing
`--libdir=otherlibdir` would result in a prefix of `/my prefix` and a libdir of
`otherlibdir`.


## Loading multiple native files

Unlike cross file, native files allow layering. More than one native file can be
loaded, with values from a previous file being overridden by the next. The
intention of this is not overriding, but to allow composing native files.

For example, if there is a project using C and C++, python 3.4-3.7, and LLVM
5-7, and it needs to build with clang 5, 6, and 7, and gcc 5.x, 6.x, and 7.x;
expressing all of these configurations in monolithic configurations would
result in 81 different native files. By layering them, it can be expressed by
just 12 native files.


## Native file locations

Like cross files, native files may be installed to user or system wide
locations, defined as:
  - $XDG_DATA_DIRS/meson/native 
    (/usr/local/share/meson/native:/usr/share/meson/native if $XDG_DATA_DIRS is
    undefined)
  - $XDG_DATA_HOME/meson/native ($HOME/.local/share/meson/native if
    $XDG_DATA_HOME is undefined)

The order of locations tried is as follows:
 - A file relative to the local dir
 - The user local location
 - The system wide locations in order

These files are not intended to be shipped by distributions, unless they are
specifically for distribution packaging, they are mainly intended for
developers.
