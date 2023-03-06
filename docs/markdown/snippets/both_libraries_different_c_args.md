## Dictionary in `<lang>_args` keyword argument

Language arguments can be a dictionary mapping the target type
(e.g. `static_library`, `shared_library`, etc). This is useful when using
`library()` or `both_libraries()` to have different flags for the shared and
static library. In that case all object files will have to be compiled
twice instead of reusing them for both libraries.

```meson
cargs = []
if host_machine.system() == 'windows' and get_option('default_library') != 'shared'
  cargs = {'static_library': '-DSTATIC_COMPILATION'}
endif

library('foo', sources, c_args: c_args)
```
