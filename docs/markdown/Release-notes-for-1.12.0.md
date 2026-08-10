---
title: Release 1.12.0
short-description: Release notes for 1.12.0
...

# New features

Meson 1.12.0 was released on 10 August 2026
## Custom dependency for atomic now works on MSVC

`dependency('atomic')` now works on MSVC >=19.35.32124.
It requires `c_std=c11` or later, otherwise the dependency will return not found.

## Support for CACHEDIR.TAG specification

A CACHEDIR.TAG file (https://bford.info/cachedir/) is now created in the build
directory as part of the setup and regenerate phases, allowing backup software
to ignore the whole directory.

## New "clippy-json" Ninja Target For rust-analyzer

A new `clippy-json` ninja target will now be generated for rust projects.

rust-analyzer supports non-cargo based projects so long as you provide it with a `rust-project.json` file and a custom "check command" to provide compiler errors.  Meson already for some time has generated a `rust-project.json` file for rust-analyzer, but had no way to hook up its rustc/clippy output to rust-analyzer.

To use the new feature, you need to override the rust-analyzer check command as shown [in the rust-analyzer documentation](https://rust-analyzer.github.io/book/non_cargo_based_projects.html), and set it to a `ninja invocation along the lines of `ninja clippy-json -C build`.

## Add a new `default()` function and object

This function and object allow setting a keyword argument to it's default value.
This is especially useful for cases when a non-default value is wanted in some
cases but not all.

For example:
```meson
library(
  ...
  name_prefix : host_machine.system() == 'windows' ? '' : default(),
)
```

## Delay install script errors to install time

Previously, `gnome.post_install` might've caused a configure to fail
due to tools such as `update-desktop-database` not being installed or
due to an `exe_wrapper` missing when cross-building glib. Those
errors will now be delayed to install time, or not emitted at all
if installing with `DESTDIR` set, since then they'll be skipped.

## find_program() now respects --force-fallback-for

If a subproject listed in --force-fallback-for provides a particular
program (via program_names in its wrapfile), find_program will use the
program from the subproject instead of looking it up from the system.

## `fs.copyfile()` now has a `build_subdir` argument

`fs.copyfile()`'s new `build_subdir` argument allows creating a file
inside a subdirectory of the current build directory.

## Added `depends` kwarg to `generator.process()`

The [[generator.process]] method now supports specifying `depends` as a kwarg
to extend the list of dependencies for generated files.

## Added `msgfmt_args` arg to `i18n.gettext`

`i18n.gettext` now supports the `msgfmt_args` argument.
This argument can be used to pass additional arguments to
`msgfmt` when building the translations.

```meson
i18n = import('i18n')
i18n.gettext('mycatalog',
             args : ['-k_', '-kN_'],
             msgfmt_args : ['--use-fuzzy'])
```

## include_directories object now have a to_list() method

The [[@inc]] object returned by [[include_directories]] now has a `to_list()` method that
returns a list of strings of absolute paths. Unless the include path is a 
system path, there will be a path for the source root and one for the build root.

```
inc = include_directories('include')
include_paths = inc.to_list()
```

## Added integer base conversions to `str.to_int()` and `int.to_string()`

Meson strings can now be converted from hexadecimal, octal, and binary
integer literals with `str.to_int()`. Integers can also be formatted back to
strings in those bases with `int.to_string(format:)`.

```meson
assert('0xff'.to_int() == 255)
assert(255.to_string(format: 'hex') == '0xff')
```

## Multiple positional arguments for `meson wrap install`

Previously `meson wrap install` only accepted a single wrap name to install.
This limitation has now been lifted, and it is now possible to specify
multiple wrap names for installation. The exit code will be non-zero
if *any* of the wraps fail to install.

## `meson format` allows `--recursive` with `--check-diff`

Previously, the `--recursive` option to `meson format` required
either `--inplace` or `--output`.  With this version, `--check-diff`
is allowed to.

## New option `--subprojects` for `meson format`

A new option `--subprojects`, to be specified together with `--recursive`,
tells `meson format` to also recurse into subprojects.

## OpenHarmony (OHOS) is now recognized as an Android subsystem

Meson now recognizes OpenHarmony / HarmonyOS (OHOS). OHOS behaves like
Android -- applications are shared libraries, shared libraries are not
versioned, and so on -- but uses musl instead of Bionic. It is therefore
modelled as an Android subsystem rather than a separate system.

Machine files select it in the `[host_machine]` section with:

```ini
[host_machine]
system = 'android'
subsystem = 'ohos'
```

With this, `host_machine.system()` is `'android'` (so all Android handling
applies, including unversioned `libfoo.so` output) while
`host_machine.subsystem()` is `'ohos'`. When cross-compiling a CMake
subproject, the toolchain file generated by the CMake module sets
`CMAKE_SYSTEM_NAME = OHOS`.

## External programs as inputs and dependencies to custom targets

Custom targets now allow specifying an external program in
the `input` and `depends` keyword arguments.  This also applies
to several methods provided by modules, as they are lowered to
custom targets internally.

## External programs as dependencies to tests

Tests now allow specifying an external program in
the `depends` keyword argument.


## Support for Python 3.7, 3.8, and 3.9 dropped

Meson 1.12 is the first version to require Python version 3.10 or greater.

Support for older versions of Python is maintained with bug fixes only for
some LTS releases. See the [FAQ
entry](FAQ.md#Do-you-at-least-support-my-ancient-python-install) for more
information.

## More types of generated files allowed by `qt.preprocess`

`qt.preprocess` now allows custom target indexes or generators
in addition to custom targets for `ui_files`, `moc_sources`
and `moc_headers`.

## The Rust module includes a basic wrapper for cbindgen

This will correctly track the config.toml, and generate a rust source from the
marked C files. This handles structured_sources correctly, and also handles
depfile generation transparently.

## Non-default members of Cargo workspaces can now be built

The new keyword argument `extra_members` to the `workspace()` method
allows configuring non-default members of a Cargo workspace.  Previously,
non-default members were never used for dependency resolution and
could not be built.

## subproject() and meson.override_find_program() now support the native keyword argument

Subprojects may now be built for the host or build machine (or both). Therefore,
in a cross compile setup, build-time dependencies can be built for the machine
running the build. When a subproject is run for the build machine it will act
just like a normal build == host setup, except that no targets will be installed.

This necessarily means that `meson.override_find_program()` must differentiate
between programs for the host and those for the build machine, as you may need
two versions of the same program, which have different outputs based on the
machine they are for. For backwards compatibility reasons the default is for the
host machine. Inside a native subproject the host and build machine will both be
the build machine.

Cargo workspaces use this feature automatically when building procedural macro
crates and their dependencies.

## `meson test` now accepts `--exclude`

`meson test` has a new `--exclude` argument to allow skipping named
tests. It takes a full test name and can be specified repeatedly. This
should help distributions that need to skip tests irrelevant for them
or known to be buggy.

## Vala cross compilation changes

Traditionally Meson has used the same Vala compiler for cross and
native compilation. It turned out that even though the Vala compiler
generated C code, the output and its dependencies are platform
dependent. Now Meson uses Vala in the same way as all other cross
compilers and it can be defined in the cross file.

## `werror=true` now applies to the linker as well

When `werror=true` is set, Meson now passes the appropriate
fatal-warnings flag to the linker (for example `--fatal-warnings`
for GNU ld, `-fatal_warnings` for Apple ld, `/WX` for MSVC link).
Previously, `werror=true` only affected compiler warnings.

## Added `win_subsystem` to `shared_library()` and `shared_module()`

Synonym for the one found in `executable()`.

Mostly useful for setting the subsystem version in PE headers.
This can affects Windows's ShimEngine, but not SxS lookups. Usually you still
want to provide a manifest when targeting modern Windows.
Sometime also useful for targeting other subsystems.

Visual Studio backends now also properly supports setting subsystem versions.

## i18n.xgettext recursive option now includes "private" dependencies

Suppose we have:

```
libA.dll -> libB.dll -> libC.dll
```

Here, `libA` links with `libB`, and `libB` links with `libC`, but `libA` does
not link with `libC` directly. So, `libC` is a "private" dependency of `libB`.
If we collect strings to translate using:

```
i18n.xgettext(libC)
i18n.xgettext(libB)
pot_file = i18n.xgettext(libA, recursive: true)
```

Previously, strings from `libC` would not be included in `pot_file`, since
`libC` is not a direct link dependency of `libA`. This has been fixed: when
the `recursive: true` option is used, `xgettext` now recursively includes
translations from all dependencies, including those of dependencies. This is
more logical, as even if `libA` does not directly link with `libC`, it may
still need translated strings from `libC`.

