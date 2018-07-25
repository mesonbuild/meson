---
short-description: Built-in options to configure project properties
...

# Built-in options

Meson provides two kinds of options: [build options provided by the
build files](Build-options.md) and built-in options that are either
universal options, base options, compiler options.

## Universal options

A list of these options can be found by running `meson --help`. All
these can be set by passing to `meson` (aka `meson setup`) in any of
these ways: `--option=value`, `--option value`, `-Doption=value`.

They can also be edited after setup using `meson configure`.

Installation options are all relative to the prefix, except:

* When the prefix is `/usr`: `sysconfdir` defaults to `/etc`, `localstatedir` defaults to `/var`, and `sharedstatedir` defaults to `/var/lib`
* When the prefix is `/usr/local`: `localstatedir` defaults to `/var/local`, and `sharedstatedir` defaults to `/var/local/lib`

| Option                               | Default value | Description |
| ------                               | ------------- | ----------- |
| prefix                               | see below     | Installation prefix |
| libdir                               | see below     | Library directory |
| libexecdir                           | libexec       | Library executable directory |
| bindir                               | bin           | Executable directory |
| sbindir                              | sbin          | System executable directory |
| includedir                           | include       | Header file directory |
| datadir                              | share         | Data file directory |
| mandir                               | share/man     | Manual page directory |
| infodir                              | share/info    | Info page directory |
| localedir                            | share/locale  | Locale data directory |
| sysconfdir                           | etc           | Sysconf data directory |
| localstatedir                        | var           | Localstate data directory |
| sharedstatedir                       | com           | Architecture-independent data directory |
| werror                               | false         | Treat warnings as erros |
| warnlevel {1, 2, 3}                  | 1             | Set the warning level. From 1 = lowest to 3 = highest |
| layout {mirror,flat}                 | mirror        | Build directory layout. |
| default-library {shared, static, both} | shared       | Default library type. |
| backend {ninja, vs,<br>vs2010, vs2015, vs2017, xcode} |               | Backend to use (default: ninja). |
| stdsplit                             |               | Split stdout and stderr in test logs. |
| errorlogs                            |               | Whether to print the logs from failing tests. |
| cross-file CROSS_FILE                |               | File describing cross compilation environment. |
| wrap-mode {default, nofallback, nodownload, forcefallback} | | Special wrap mode to use |


`prefix` defaults to `C:/` on Windows, and `/usr/local/` otherwise. You should always
override this value.

`libdir` is automatically detected based on your platform, but the
implementation is [currently buggy](https://github.com/mesonbuild/meson/issues/2038)
on Linux platforms.

There are various other options to set, for instance the backend to use and
the path to the cross-file while cross compiling, which won't be repeated here.
Please see the output of `meson --help`.

## Base options

These are set in the same way as universal options, but cannot be shown in the
output of `meson --help` because they depend on both the current platform and
the compiler that will be selected. The only way to see them is to setup
a builddir and then run `meson configure` on it with no options.

The following options are available. Note that they may not be available on all
platforms or with all compilers:

| Option      | Default value | Possible values         | Description |
| ----------- | ------------- | ---------------         | ----------- |
| b_asneeded  | true          | true, false             | Use -Wl,--as-needed when linking |
| b_bitcode   | false         | true, false             | Embed Apple bitcode, see below |
| b_colorout  | always        | auto, always, never     | Use colored output |
| b_coverage  | false         | true, false             | Enable coverage tracking |
| b_crtlib    | from_buildtype| none, md, mdd, mt, mtd, from_buildtype | VS runtime library to use (since 0.48.0) |
| b_lundef    | true          | true, false             | Don't allow undefined symbols when linking |
| b_lto       | false         | true, false             | Use link time optimization |
| b_ndebug    | false         | true, false, if-release | Disable asserts |
| b_pch       | true          | true, false             | Use precompiled headers |
| b_pgo       | off           | off, generate, use      | Use profile guided optimization |
| b_sanitize  | none          | see below               | Code sanitizer to use |
| b_staticpic | true          | true, false             | Build static libraries as position independent |

The value of `b_sanitize` can be one of: `none`, `address`, `thread`,
`undefined`, `memory`, `address,undefined`.

### Notes about Apple Bitcode support

`b_bitcode` will pass `-fembed-bitcode` while compiling and will pass
`-Wl,-bitcode_bundle` while linking. These options are incompatible with
`b_asneeded`, so that option will be silently disabled.

[Shared modules](#Reference-manual.md#shared_module) will not have bitcode
embedded because `-Wl,-bitcode_bundle` is incompatible with both `-bundle` and
`-Wl,-undefined,dynamic_lookup` which are necessary for shared modules to work.

## Compiler options

Same caveats as base options above.

The following options are available. Note that both the options themselves and
the possible values they can take will depend on the target platform or
compiler being used:

| Option       | Default value | Possible values                          | Description |
| ------       | ------------- | ---------------                          | ----------- |
| c_args       |               | free-form comma-separated list           | C compile arguments to use |
| c_link_args  |               | free-form comma-separated list           | C link arguments to use |
| c_std        | none          | none, c89, c99, c11, gnu89, gnu99, gnu11 | C language standard to use |
| c_winlibs    | see below     | free-form comma-separated list           | Standard Windows libs to link against |
| cpp_args     |               | free-form comma-separated list           | C++ compile arguments to use |
| cpp_link_args|               | free-form comma-separated list           | C++ link arguments to use |
| cpp_std      | none          | none, c++98, c++03, c++11, c++14, c++17, <br/>c++1z, gnu++03, gnu++11, gnu++14, gnu++17, gnu++1z | C++ language standard to use |
| cpp_debugstl | false         | true, false                              | C++ STL debug mode |
| cpp_eh       | sc            | none, a, s, sc                           | C++ exception handling type |
| cpp_winlibs  | see below     | free-form comma-separated list           | Standard Windows libs to link against |

The default values of `c_winlibs` and `cpp_winlibs` are in compiler-specific
argument forms, but the libraries are: kernel32, user32, gdi32, winspool,
shell32, ole32, oleaut32, uuid, comdlg32, advapi32
