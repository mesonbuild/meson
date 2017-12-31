# Pkgconfig module

This module is a simple generator for
[pkg-config](https://pkg-config.freedesktop.org/) files.

## Usage

To use this module, just do: **`pkg = import('pkgconfig')`**. The
following function will then be available as `pkg.generate()`. You
can, of course, replace the name `pkg` with anything else.

### pkg.generate()

The generated file's properties are specified with the following
keyword arguments.

- `description` a string describing the library
- `extra_cflags` a list of extra compiler flags to be added to the
  `Cflags` field after the header search path
- `filebase`, the base name to use for the pkg-config file, as an
  example the value of `libfoo` would produce a pkg-config file called
  `libfoo.pc`
- `install_dir` the directory to install to, defaults to the value of
  option `libdir` followed by `/pkgconfig`
- `libraries` a list of built libraries (usually results of
  shared_library) that the user needs to link against. Arbitraty strings can
  also be provided and they will be added into the `Libs` field. Since 0.45.0
  dependencies of built libraries will be automatically added to `Libs.private`
  field. If a dependency is provided by pkg-config then it will be added in
  `Requires.private` instead. Other type of dependency objects can also be passed
  and will result in their `link_args` and `compile_args` to be added to `Libs`
  and `Cflags` fields.
- `libraries_private` list of built libraries or strings to put in the
  `Libs.private` field. Since 0.45.0 it can also contain dependency objects,
  their `link_args` will be added to `Libs.private`.
- `name` the name of this library
- `subdirs` which subdirs of `include` should be added to the header
  search path, for example if you install headers into
  `${PREFIX}/include/foobar-1`, the correct value for this argument
  would be `foobar-1`
- `requires` list of strings to put in the `Requires` field
- `requires_private` list of strings to put in the `Requires.private`
  field
- `url` a string with a url for the library
- `variables` a list of strings with custom variables to add to the
  generated file. The strings must be in the form `name=value` and may
  reference other pkgconfig variables,
  e.g. `datadir=${prefix}/share`. The names `prefix`, `libdir` and
  `installdir` are reserved and may not be used.
- `version` a string describing the version of this library
- `d_module_versions` a list of module version flags used when compiling
   D sources referred to by this pkg-config file
