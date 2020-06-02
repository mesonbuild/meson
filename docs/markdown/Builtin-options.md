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
these ways: `--option=value`, `--option value`, `-Doption=value`, or
by setting them inside `default_options` of `project()` in your `meson.build`.

For legacy reasons `--warnlevel` is the cli argument for the `warning_level` option.

They can also be edited after setup using `meson configure`.

Installation options are all relative to the prefix, except:

* When the prefix is `/usr`: `sysconfdir` defaults to `/etc`, `localstatedir` defaults to `/var`, and `sharedstatedir` defaults to `/var/lib`
* When the prefix is `/usr/local`: `localstatedir` defaults to `/var/local`, and `sharedstatedir` defaults to `/var/local/lib`

### Directories

| Option                               | Default value | Description |
| ------                               | ------------- | ----------- |
| prefix                               | see below     | Installation prefix |
| bindir                               | bin           | Executable directory |
| datadir                              | share         | Data file directory |
| includedir                           | include       | Header file directory |
| infodir                              | share/info    | Info page directory |
| libdir                               | see below     | Library directory |
| libexecdir                           | libexec       | Library executable directory |
| localedir                            | share/locale  | Locale data directory |
| localstatedir                        | var           | Localstate data directory |
| mandir                               | share/man     | Manual page directory |
| sbindir                              | sbin          | System executable directory |
| sharedstatedir                       | com           | Architecture-independent data directory |
| sysconfdir                           | etc           | Sysconf data directory |


`prefix` defaults to `C:/` on Windows, and `/usr/local` otherwise. You should always
override this value.

`libdir` is automatically detected based on your platform, it should be
correct when doing "native" (build machine == host machine) compilation. For
cross compiles meson will try to guess the correct libdir, but it may not be
accurate, especially on Linux where different distributions have different
defaults. Using a [cross file](Cross-compilation.md#defining-the-environment),
particularly the paths section may be necessary.

### Core options

Options that are labeled "per machine" in the table are set per machine. See
the [specifying options per machine](#Specifying-options-per-machine) section
for details.

| Option                               | Default value | Description                                                    | Is per machine |
| ------                               | ------------- | -----------                                                    | -------------- |
| auto_features {enabled, disabled, auto} | auto       | Override value of all 'auto' features                          | no             |
| backend {ninja, vs,<br>vs2010, vs2015, vs2017, vs2019, xcode} | ninja | Backend to use                                | no             |
| buildtype {plain, debug,<br>debugoptimized, release, minsize, custom} | debug |  Build type to use                    | no             |
| debug                                | true          | Debug                                                          | no             |
| default_library {shared, static, both} | shared      | Default library type                                           | no             |
| errorlogs                            | true          | Whether to print the logs from failing tests.                  | no             |
| install_umask {preserve, 0000-0777}  | 022           | Default umask to apply on permissions of installed files       | no             |
| layout {mirror,flat}                 | mirror        | Build directory layout                                         | no             |
| optimization {0, g, 1, 2, 3, s}      | 0             | Optimization level                                             | no             |
| pkg_config_path {OS separated path}  | ''            | Additional paths for pkg-config to search before builtin paths | yes            |
| cmake_prefix_path                    | []            | Additional prefixes for cmake to search before builtin paths   | yes            |
| stdsplit                             | true          | Split stdout and stderr in test logs                           | no             |
| strip                                | false         | Strip targets on install                                       | no             |
| unity {on, off, subprojects}         | off           | Unity build                                                    | no             |
| unity_size {>=2}                     | 4             | Unity file block size                                          | no             |
| warning_level {0, 1, 2, 3}           | 1             | Set the warning level. From 0 = none to 3 = highest            | no             |
| werror                               | false         | Treat warnings as errors                                       | no             |
| wrap_mode {default, nofallback,<br>nodownload, forcefallback} | default | Wrap mode to use                            | no             |
| force_fallback_for                   | []            | Force fallback for those dependencies                          | no             |

<a name="build-type-options"></a>
For setting optimization levels and toggling debug, you can either set the
`buildtype` option, or you can set the `optimization` and `debug` options which
give finer control over the same. Whichever you decide to use, the other will
be deduced from it. For example, `-Dbuildtype=debugoptimized` is the same as
`-Ddebug=true -Doptimization=2` and vice-versa. This table documents the
two-way mapping:

| buildtype      | debug | optimization |
| ---------      | ----- | ------------ |
| plain          | false | 0            |
| debug          | true  | 0            |
| debugoptimized | true  | 2            |
| release        | false | 3            |
| minsize        | true  | s            |

All other combinations of `debug` and `optimization` set `buildtype` to `'custom'`.

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
| b_lundef    | true          | true, false             | Don't allow undefined symbols when linking |
| b_lto       | false         | true, false             | Use link time optimization |
| b_ndebug    | false         | true, false, if-release | Disable asserts |
| b_pch       | true          | true, false             | Use precompiled headers |
| b_pgo       | off           | off, generate, use      | Use profile guided optimization |
| b_sanitize  | none          | see below               | Code sanitizer to use |
| b_staticpic | true          | true, false             | Build static libraries as position independent |
| b_pie       | false         | true, false             | Build position-independent executables (since 0.49.0)|
| b_vscrt     | from_buildtype| none, md, mdd, mt, mtd, from_buildtype | VS runtime library to use (since 0.48.0) |

The value of `b_sanitize` can be one of: `none`, `address`, `thread`,
`undefined`, `memory`, `address,undefined`.

<a name="b_vscrt-from_buildtype"></a>
The default value of `b_vscrt` is `from_buildtype`. In that case, the following
table is used internally to pick the CRT compiler arguments based on the value
of the `buildtype` option:

| buildtype      | Visual Studio CRT |
| --------       | ----------------- |
| debug          | `/MDd`            |
| debugoptimized | `/MD`             |
| release        | `/MD`             |
| minsize        | `/MD`             |
| custom         | error!            |

### Notes about Apple Bitcode support

`b_bitcode` will pass `-fembed-bitcode` while compiling and will pass
`-Wl,-bitcode_bundle` while linking. These options are incompatible with
`b_asneeded`, so that option will be silently disabled.

[Shared modules](Reference-manual.md#shared_module) will not have bitcode
embedded because `-Wl,-bitcode_bundle` is incompatible with both `-bundle` and
`-Wl,-undefined,dynamic_lookup` which are necessary for shared modules to work.

## Compiler options

Same caveats as base options above.

The following options are available. Note that both the options themselves and
the possible values they can take will depend on the target platform or
compiler being used:

| Option           | Default value | Possible values                          | Description |
| ------           | ------------- | ---------------                          | ----------- |
| c_args           |               | free-form comma-separated list           | C compile arguments to use |
| c_link_args      |               | free-form comma-separated list           | C link arguments to use |
| c_std            | none          | none, c89, c99, c11, c17, c18, gnu89, gnu99, gnu11, gnu17, gnu18 | C language standard to use |
| c_winlibs        | see below     | free-form comma-separated list           | Standard Windows libs to link against |
| c_thread_count   | 4             | integer value ≥ 0                        | Number of threads to use with emcc when using threads |
| cpp_args         |               | free-form comma-separated list           | C++ compile arguments to use |
| cpp_link_args    |               | free-form comma-separated list           | C++ link arguments to use |
| cpp_std          | none          | none, c++98, c++03, c++11, c++14, c++17, <br/>c++1z, gnu++03, gnu++11, gnu++14, gnu++17, gnu++1z, <br/> vc++14, vc++17, vc++latest | C++ language standard to use |
| cpp_debugstl     | false         | true, false                              | C++ STL debug mode |
| cpp_eh           | default       | none, default, a, s, sc                  | C++ exception handling type |
| cpp_rtti         | true          | true, false                              | Whether to enable RTTI (runtime type identification) |
| cpp_thread_count | 4             | integer value ≥ 0                        | Number of threads to use with emcc when using threads |
| cpp_winlibs      | see below     | free-form comma-separated list           | Standard Windows libs to link against |
| fortran_std      | none          | [none, legacy, f95, f2003, f2008, f2018] | Fortran language standard to use |

The default values of `c_winlibs` and `cpp_winlibs` are in compiler-specific
argument forms, but the libraries are: kernel32, user32, gdi32, winspool,
shell32, ole32, oleaut32, uuid, comdlg32, advapi32.

All these `<lang>_*` options are specified per machine. See below in the
[specifying options per machine](#Specifying-options-per-machine) section on
how to do this in cross builds.

When using MSVC, `cpp_eh=none` will result in no exception flags being passed,
while the `cpp_eh=[value]` will result in `/EH[value]`.
Since *0.51.0* `cpp_eh=default` will result in `/EHsc` on MSVC. When using
gcc-style compilers, nothing is passed (allowing exceptions to work), while
`cpp_eh=none` passes `-fno-exceptions`.

Since *0.54.0* The `<lang>_thread_count` option can be used to control the
value passed to `-s PTHREAD_POOL_SIZE` when using emcc. No other c/c++
compiler supports this option.

## Specifying options per machine

Since *0.51.0*, some options are specified per machine rather than globally for
all machine configurations. Prefixing the option with `build.` just affects the
build machine configuration, while unprefixed just affects the host machine
configuration, respectively. For example:

 - `build.pkg_config_path` controls the paths pkg-config will search for just
   `native: true` dependencies (build machine).

 - `pkg_config_path` controls the paths pkg-config will search for just
   `native: false` dependencies (host machine).

This is useful for cross builds. In the native builds, build = host, and the
unprefixed option alone will suffice.

Prior to *0.51.0*, these options just effected native builds when specified on
the command line, as there was no `build.` prefix. Similarly named fields in
the `[properties]` section of the cross file would effect cross compilers, but
the code paths were fairly different allowing differences in behavior to crop
out.
