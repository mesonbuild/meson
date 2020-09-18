## HDF5 dependency improvements

HDF5 has been improved so that the internal representations have been split.
This allows selecting pkg-config and config-tool dependencies separately.
Both work as proper dependencies of their type, so `get_variable` and similar
now work correctly.

It has also been fixed to use the selected compiler for the build instead of
the default compiler.
