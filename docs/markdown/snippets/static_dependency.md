## Filtering static libraries in `dependency()`'s static kwarg

A list of Unix shell-style wildcards strings can now be passed to `dependency()`'s
static kwarg. A static library will be used only if its absolute path matches at
least one of the patterns, otherwsise it will be kept dynamic.

```meson
# Do not static link basic system libraries likes libz
glib_dep = dependency('glib-2.0', static : ['*glib*'])
```
