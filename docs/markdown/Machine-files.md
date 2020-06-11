# Cross and Native File reference

Cross and native files are nearly identical, but not completely. This is the
documentation on the common values used by both, for the specific values of
one or the other see the [cross compilation](Cross-compilation.md) and [native
environments](Native-environments.md).

## Sections

The following sections are allowed:
- constants
- binaries
- paths
- properties

### constants

*Since 0.55.0*

String and list concatenation is supported using the `+` operator, joining paths
is supported using the `/` operator.
Entries defined in the `[constants]` section can be used in any other section
(they are always parsed first), entries in any other section can be used only
within that same section and only after it has been defined.

```ini
[constants]
toolchain = '/toolchain'
common_flags = ['--sysroot=' + toolchain / 'sysroot']

[properties]
c_args = common_flags + ['-DSOMETHING']
cpp_args = c_args + ['-DSOMETHING_ELSE']

[binaries]
c = toolchain / 'gcc'
```

This can be useful with cross file composition as well. A generic cross file
could be composed with a platform specific file where constants are defined:
```ini
# aarch64.ini
[constants]
arch = 'aarch64-linux-gnu'
```

```ini
# cross.ini
[binaries]
c = arch + '-gcc'
cpp = arch + '-g++'
strip = arch + '-strip'
pkgconfig = arch + '-pkg-config'
...
```

This can be used as `meson setup --cross-file aarch64.ini --cross-file cross.ini builddir`.

Note that file composition happens before the parsing of values. The example
below results in `b` being `'HelloWorld'`:
```ini
# file1.ini:
[constants]
a = 'Foo'
b = a + 'World'
```

```ini
#file2.ini:
[constants]
a = 'Hello'
```

The example below results in an error when file1.ini is included before file2.ini
because `b` would be defined before `a`:
```ini
# file1.ini:
[constants]
b = a + 'World'
```

```ini
#file2.ini:
[constants]
a = 'Hello'
```

### Binaries

The binaries section contains a list of binaries. These can be used
internally by meson, or by the `find_program` function:

Compilers and linkers are defined here using `<lang>` and `<lang>_ld`.
`<lang>_ld` is special because it is compiler specific. For compilers like
gcc and clang which are used to invoke the linker this is a value to pass to
their "choose the linker" argument (-fuse-ld= in this case). For compilers
like MSVC and Clang-Cl, this is the path to a linker for meson to invoke,
such as `link.exe` or `lld-link.exe`. Support for ls is *new in 0.53.0*

*changed in 0.53.1* the `ld` variable was replaced by `<lang>_ld`, because it
*regressed a large number of projects. in 0.53.0 the `ld` variable was used
instead.

Native example:

```ini
c = '/usr/bin/clang'
c_ld = 'lld'
sed = 'C:\\program files\\gnu\\sed.exe'
llvm-config = '/usr/lib/llvm8/bin/llvm-config'
```

Cross example:

```ini
c = '/usr/bin/i586-mingw32msvc-gcc'
cpp = '/usr/bin/i586-mingw32msvc-g++'
c_ld = 'gold'
cpp_ld = 'gold'
ar = '/usr/i586-mingw32msvc/bin/ar'
strip = '/usr/i586-mingw32msvc/bin/strip'
pkgconfig = '/usr/bin/i586-mingw32msvc-pkg-config'
```

An incomplete list of internally used programs that can be overridden here is:
- cmake
- cups-config
- gnustep-config
- gpgme-config
- libgcrypt-config
- libwmf-config
- llvm-config
- pcap-config
- pkgconfig
- sdl2-config
- wx-config (or wx-3.0-config or wx-config-gtk)

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

### Properties

*New in native files in 0.54.0*, always in cross files.

In addition to special data that may be specified in cross files, this
section may contain random key value pairs accessed using the
`meson.get_external_property()`

## Properties

*New for native files in 0.54.0*

The properties section can contain any variable you like, and is accessed via
`meson.get_external_property`, or `meson.get_cross_property`.

## Loading multiple machine files

Native files allow layering (cross files can be layered since meson 0.52.0).
More than one native file can be loaded, with values from a previous file being
overridden by the next. The intention of this is not overriding, but to allow
composing native files. This composition is done by passing the command line
argument multiple times:

```console
meson setup builddir/ --cross-file first.ini --cross-file second.ini --cross-file thrid.ini
```

In this case `first.ini` will be loaded, then `second.ini`, with values from
`second.ini` replacing `first.ini`, and so on.

For example, if there is a project using C and C++, python 3.4-3.7, and LLVM
5-7, and it needs to build with clang 5, 6, and 7, and gcc 5.x, 6.x, and 7.x;
expressing all of these configurations in monolithic configurations would
result in 81 different native files. By layering them, it can be expressed by
just 12 native files.
