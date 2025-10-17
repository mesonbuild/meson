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
OBJC and OBJC++ languages. The content of the header is static regardless
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
  building a static library and thus cannot be used with `both_libraries()` or
  `library()` when `default_library=both`. If set to `false` (the default) and
  the generated header is used in a static library,
  `-D<NAMESPACE>_STATIC_COMPILATION` C-flag must be defined manually both when
  compiling the library AND when compiling applications that use the library API.
  In that case it typically should be defined in
  `declare_dependency(..., compile_args: [])` and
  `pkgconfig.generate(..., extra_cflags: [])`.
  Note that when building both shared and static libraries on Windows,
  applications cannot currently rely on `pkg-config` to define this macro.
  See https://github.com/mesonbuild/meson/pull/14829.

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
default_library = get_option('default_library')
snippets = import('snippets')
apiheader = snippets.symbol_visibility_header('apiconfig.h',
  static_only: default_library == 'static')
install_headers(apiheader, 'lib.h', subdir: 'mylib')
lib = library('mylib', 'lib.c',
  gnu_symbol_visibility: 'hidden',
  c_args: ['-DMYLIB_COMPILATION'],
  c_static_args: ['-DMYLIB_STATIC_COMPILATION'],
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

### symbol_visibility_string()

Same as [[symbol_visibility_header]] but takes no positional argument and
returns the snippet as a string instead of generating a header file.

This is intended to be used with [[configure_file]] to insert the snippet in
a header file that contains other definitions.
`config.h.in`
```c
#define SOMETHING

@visibility_macro@
```

```meson
str = snippets.symbol_visibility_string()
config_h = configure_file(
  input: 'config.h.in',
  output: 'config.h',
  configuration: {'visibility_macro': str},
)
```
