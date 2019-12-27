# Release notes

## find_program(), executable(), and custom_target() object methods

The object returned by `find_program()` supported only a `path()`
method while `executable()` and `custom_target()` supported only a
`full_path()` method.  With this release all three objects support both
methods; however, the `full_path()` method is deprecated and might be
removed at some future date.  See issue #6375.
