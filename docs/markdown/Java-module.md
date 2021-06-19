# Java Module

*Added 0.60.0*

## Functions

### `generate_native_header()`

This function will generate a header file for use in Java native module
development by reading the supplied Java file for `native` method declarations.

Keyword arguments:

- `package`: The [package](https://en.wikipedia.org/wiki/Java_package) of the
file. If left empty, Meson will assume that there is no package.
