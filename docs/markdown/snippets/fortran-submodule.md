## Initial Fortran 2008 `submodule` support

The Fortran `module` detection was improved by regular expression to distinguish between `module`, `module procedure/subroutine/function` and `submodule`.
This allows us to enable initial support for Fortran 2008 `submodule` with certain restrictions.
A submodule dependency resolver has not yet been implemented, so the workaround is to use a Unity build.

1. All files referring to the `submodule`, including the file containing the `submodule`, must be specified within one target, . This can be accomplished with Meson `if` statements for the case where compile-time submodule switching is needed. E.g., distinct submodules to handle file IO with HDF5 vs. NetCDF4 libraries based on which library is available at compile-time.
2. at configure time, use the `--unity on` option.

