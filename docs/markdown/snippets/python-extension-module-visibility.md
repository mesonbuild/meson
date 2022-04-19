## Python extension modules now build with hidden visibility

Python extension modules are usually expected to only export a single symbol,
decorated with the `PyMODINIT_FUNC` macro and providing the module entry point.
On versions of python >= 3.9, the python headers contain GNU symbol visibility
attributes to mark the init function with default visibility; it is then safe
to set the [[shared_module]] inherited kwarg `gnu_symbol_visibility: 'hidden'`.

In the interest of doing the right thing out of the box, this is now the
default for extension modules for found installations that are new enough to
have this set, which is not expected to break anything, but remains possible to
set explicitly (in which case that will take precedence).
