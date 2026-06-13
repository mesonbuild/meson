## New `requires_shared` keyword argument for `pkgconfig.generate()`

The new `requires_shared` keyword argument to `pkgconfig.generate()` can
be used to override the automatically-generated `Requires.private` entries
for shared libraries.  This is useful when a shared library's headers do
not expose its dependency's headers, avoiding unnecessary build dependencies
for consumers of the `.pc` file.
