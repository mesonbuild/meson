## New variable type for dependencies "meson"

For dependencies that are implemented in meson itself (like threads), a new
variable name has been added "meson". Meson can use this to encode specific
information about dependencies that would be normally available from other
methods like "pkg-config" or "cmake"

```meson
dep_threads = dependency('threads')
if dep_threads.get_variable(meson : 'type') == 'foo'
  ...
endif
```
