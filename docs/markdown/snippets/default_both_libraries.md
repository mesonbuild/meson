## New built-in option for default both_libraries

`both_libraries` targets used to be considered as a shared library by default.
There is now the `default_both_libraries` option to change this default.

When `default_both_libraries` is 'auto', [[both_libraries]] with dependencies
that are [[@both_libs]] themselves will link with the same kind of library.
For example, if `libA` is a [[@both_libs]] and `libB` is a [[@both_libs]]
linked with `libA` (or with an internal dependency on `libA`),
the static lib of `libB` will link with the static lib of `libA`, and the
shared lib of `libA` will link with the shared lib of `libB`.
