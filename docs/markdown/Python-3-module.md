# Python 3 module

This module provides support for dealing with Python 3. It has the
following methods.

## find_python

This is a cross platform way of finding the Python 3 executable, which
may have a different name on different operating systems. Returns an
[external program](Reference-manual.html#external-program-object) object.

*Added 0.38.0*

## extension_module

Creates a `shared_module` target that is named according to the naming
conventions of the target platform. All positional and keyword
arguments are the same as for
[shared_module](Reference-manual.md#shared_module).

`extension_module` does not add any dependencies to the library so user may
need to add `dependencies : dependency('python3')`, see
[Python3 dependency](Dependencies.md#Python3).

*Added 0.38.0*

## language_version

Returns a string with the Python language version such as `3.5`.

*Added 0.40.0*

## sysconfig_path

Returns the Python sysconfig path without prefix, such as
`lib/python3.6/site-packages`.

*Added 0.40.0*
