## Search directories for `find_program()`

It is now possible to give a list of absolute paths where `find_program()` should
also search, using the `dirs` keyword argument.

For example on Linux `/sbin` and `/usr/sbin` are not always in the `$PATH`:
```meson
prog = find_program('mytool', dirs : ['/usr/sbin', '/sbin'])
```
