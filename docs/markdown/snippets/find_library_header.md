## Find library with its headers

The `find_library()` method can now also verify if the library's headers are
found in a single call, using the `has_header()` method internally.

```meson
# Aborts if the 'z' library is found but not its header file
zlib = find_library('z', has_headers : 'zlib.h')
# Returns not-found if the 'z' library is found but not its header file
zlib = find_library('z', has_headers : 'zlib.h', required : false)
```

Any keyword argument with the `header_` prefix passed to `find_library()` will
be passed to the `has_header()` method with the prefix removed.

```meson
libfoo = find_library('foo',
  has_headers : ['foo.h', 'bar.h'],
  header_prefix : '#include <baz.h>',
  header_include_directories : include_directories('.'))
```
