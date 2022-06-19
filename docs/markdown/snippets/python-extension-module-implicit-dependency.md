## Python extension modules now depend on the python library by default

Python extension modules are usually expected to link to the python library
and/or its headers in order to build correctly (via the default `embed: false`,
which may not actually link to the library itself). This means that every
single use of `.extension_module()` needed to include the `dependencies:
py_installation.dependency()` kwarg explicitly.

In the interest of doing the right thing out of the box, this is now the
default for extension modules that don't already include a dependency on
python. This is not expected to break anything, because it should always be
needed. Nevertheless, `py_installation.dependency().partial_dependency()` will
be detected as already included while providing no compile/link args.
