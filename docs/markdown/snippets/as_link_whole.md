## `dep.as_link_whole()`

Dependencies created with `declare_dependency()` now has new method `as_link_whole()`.
It returns a copy of the dependency object with all link_with arguments changed
to link_whole. This is useful for example for fallback dependency from a
subproject built with `default_library=static`.

```meson
somelib = static_library('somelib', ...)
dep = declare_dependency(..., link_with: somelib)
library('someotherlib', ..., dependencies: dep.as_link_whole())
```
