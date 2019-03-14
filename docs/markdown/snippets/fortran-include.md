## Fortran `include` statements recursively parsed

While non-standard and generally not recommended, some legacy Fortran programs use `include` directives to inject code inline.
Since v0.51, Meson can handle Fortran `include` directives recursively.

DO NOT list `include` files as sources for a target, as in general their syntax is not correct as a standalone target.
In general `include` files are meant to be injected inline as if they were copy and pasted into the source file.

`include` was never standard and was superceded by Fortran 90 `module`.

The `include` file is only recognized by Meson if it has a Fortran file suffix, such as `.f` `.F` `.f90` `.F90` or similar.
This is to avoid deeply nested scanning of large external legacy C libraries that only interface to Fortran by `include biglib.h` or similar.
