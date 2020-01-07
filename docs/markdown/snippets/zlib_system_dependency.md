## Add a system type dependency for zlib

This allows zlib to be detected on macOS and FreeBSD without the use of
pkg-config or cmake, neither of which are part of the base install on those
OSes (but zlib is).

A side effect of this change is that `dependency('zlib')` also works with
cmake instead of requiring `dependency('ZLIB')`.
