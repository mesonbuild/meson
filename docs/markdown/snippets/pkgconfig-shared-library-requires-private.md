## `Requires.private` includes dependencies of shared libraries

When a `.pc` file is created for a `shared_library()`, its `Requires.private`
line now always includes the dependencies of the shared library.  These are used
when `pkg-config` or `pkgconf` are invoked with `--cflags`.  Previously,
the line was included for shared libraries created with `library()` (even
if the `default_library` option was set to `shared`), whereas now
`library()` and `shared_library()` behave in the same way.
