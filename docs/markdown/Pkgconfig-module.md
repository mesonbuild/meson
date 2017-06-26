# Pkgconfig module

This module is a simple generator for [pkg-config](https://pkg-config.freedesktop.org/) files.

## Usage

To use this module, just do: **`pkg = import('pkgconfig')`**. The following function will then be available as `pkg.generate()`. You can, of course, replace the name `pkg` with anything else.

### pkg.generate()

The generated file's properties are specified with the following keyword arguments.

- `libraries` a list of built libraries (usually results of shared_library) that the user needs to link against
- `version` a string describing the version of this library
- `name` the name of this library
- `description` a string describing the library
- `filebase`, the base name to use for the pkg-config file, as an example the value of `libfoo` would produce a pkg-config file called `libfoo.pc`
- `subdirs` which subdirs of `include` should be added to the header search path, for example if you install headers into `${PREFIX}/include/foobar-1`, the correct value for this argument would be `foobar-1`
- `requires` list of strings to put in the `Requires` field
- `requires_private` list of strings to put in the `Requires.private` field
- `libraries_private` list of strings to put in the `Libraries.private` field
- `install_dir` the directory to install to, defaults to the value of option `libdir` followed by `/pkgconfig`
- `extra_cflags` a list of extra compiler flags to be added to the `Cflags` field after the header search path
- `variables` a list of strings with custom variables to add to the generated file. The strings must be in the form `name=value` and may reference other pkgconfig variables, e.g. `datadir=${prefix}/share`. The names `prefix`, `libdir` and `installdir` are reserved and may not be used.
