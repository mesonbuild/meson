---
short-description: Code snippets module
...

# Snippets module

*(new in 1.10.0)*

This module provides helpers to generate commonly useful code snippets.

## Functions

### symbol_visibility_header()

```meson
snippets.symbol_visibility_header(header_name,
  namespace: str
  api: str
  compilation: str
  static_compilation: str
  static_only: bool
)
```

Generate a header file that defines macros to be used to mark all public APIs
of a library. Depending on the platform, this will typically use
`__declspec(dllexport)`, `__declspec(dllimport)` or
`__attribute__((visibility("default")))`. It is compatible with C, C++,
ObjC and ObjC++ languages. The content of the header is static regardless
of the compiler used.

The first positional argument is the name of the header file to be generated.
It also takes the following keyword arguments:

- `namespace`: Prefix for generated macros, defaults to the current project name.
  It will be converted to upper case with all non-alphanumeric characters replaced
  by an underscore `_`. It is only used for `api`, `compilation` and
  `static_compilation` default values.
- `api`: Name of the macro used to mark public APIs. Defaults to `<NAMESPACE>_API`.
- `compilation`: Name of a macro defined only when compiling the library.
   Defaults to `<NAMESPACE>_COMPILATION`.
- `static_compilation`: Name of a macro defined only when compiling or using
  static library. Defaults to `<NAMESPACE>_STATIC_COMPILATION`.
- `static_only`: If set to true, `<NAMESPACE>_STATIC_COMPILATION` is defined
  inside the generated header. In that case the header can only be used for
  building a static library. By default it is `true` when `default_library=static`,
  and `false` otherwise. [See below for more information](#static_library)

Projects that define multiple shared libraries should typically have
one header per library, with a different namespace.

The generated header file should be installed using `install_headers()`.

`meson.build`:
```meson
project('mylib', 'c')
subdir('mylib')
```

`mylib/meson.build`:
```meson
snippets = import('snippets')
apiheader = snippets.symbol_visibility_header('apiconfig.h')
install_headers(apiheader, 'lib.h', subdir: 'mylib')
lib = library('mylib', 'lib.c',
  gnu_symbol_visibility: 'hidden',
  c_args: ['-DMYLIB_COMPILATION'],
)
```

`mylib/lib.h`
```c
#include <mylib/apiconfig.h>
MYLIB_API int do_stuff();
```

`mylib/lib.c`
```c
#include "lib.h"
int do_stuff() {
  return 0;
}
```

#### Static library

When building both static and shared libraries on Windows (`default_library=both`),
`-D<NAMESPACE>_STATIC_COMPILATION` must be defined only for the static library,
using `c_static_args`. This causes Meson to compile the library twice.

```meson
if host_system == 'windows'
  static_arg = ['-DMYLIB_STATIC_COMPILATION']
else
  static_arg = []
endif
lib = library('mylib', 'lib.c',
  gnu_symbol_visibility: 'hidden',
  c_args: ['-DMYLIB_COMPILATION'],
  c_static_args: static_arg
)
```

`-D<NAMESPACE>_STATIC_COMPILATION` C-flag must be defined when compiling
applications that use the library API. It typically should be defined in
`declare_dependency(..., compile_args: [])` and
`pkgconfig.generate(..., extra_cflags: [])`.

Note that when building both shared and static libraries on Windows,
applications cannot currently rely on `pkg-config` to define this macro.
See https://github.com/mesonbuild/meson/pull/14829.
